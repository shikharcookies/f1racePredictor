"""CrossRaceModel: XGBoost + RF + LR ensemble for cross-race podium prediction."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

from app.models import CircuitAccuracy, CrossRaceMetrics, PodiumPredictionResult
from app.pipeline.feature_engineer import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


class CrossRaceModel:
    def __init__(self) -> None:
        self._clf = None
        self._scaler: StandardScaler | None = None
        self._metrics: CrossRaceMetrics | None = None
        self._circuit_accuracy: list[CircuitAccuracy] = []
        self._trained: bool = False

    def train(self, dataset: pd.DataFrame) -> None:
        """Train XGBoost+RF+LR ensemble with temporal split."""
        if dataset.empty:
            logger.warning("Empty dataset passed to CrossRaceModel.train()")
            return

        df = dataset.dropna(subset=["podium"]).copy()
        df["podium"] = df["podium"].astype(int)

        # Try 2022-2024 train / 2025+ test first for more training data
        train_df = df[df["year"].isin([2022, 2023, 2024])]
        test_df = df[df["year"] >= 2025]

        # Fall back to 2022-2023 train / 2024+ test if not enough test data
        if len(test_df) < 20:
            train_df = df[df["year"].isin([2022, 2023])]
            test_df = df[df["year"] >= 2024]

        if len(train_df) < 100:
            logger.warning("Training set has only %d rows.", len(train_df))

        if train_df.empty:
            logger.warning("No training data available.")
            return

        X_train = train_df[FEATURE_COLUMNS].fillna(0).values
        y_train = train_df["podium"].values

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        self._scaler = scaler

        # Build ensemble
        estimators = []

        if XGBOOST_AVAILABLE:
            neg = int((y_train == 0).sum())
            pos = int((y_train == 1).sum())
            scale_pos = neg / max(pos, 1)
            xgb = XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=scale_pos,
                eval_metric="logloss",
                random_state=42,
                verbosity=0,
            )
            estimators.append(("xgb", xgb))
            logger.info("XGBoost included in ensemble (scale_pos_weight=%.1f)", scale_pos)

        rf = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        estimators.append(("rf", rf))

        lr = LogisticRegression(
            C=0.5,
            class_weight="balanced",
            max_iter=500,
            random_state=42,
        )
        estimators.append(("lr", lr))

        if len(estimators) > 1:
            clf = VotingClassifier(estimators=estimators, voting="soft")
        else:
            clf = estimators[0][1]

        clf.fit(X_train_scaled, y_train)
        self._clf = clf

        training_race_count = train_df["gp_slug"].nunique() if "gp_slug" in train_df.columns else len(train_df)
        test_race_count = test_df["gp_slug"].nunique() if "gp_slug" in test_df.columns else 0

        if not test_df.empty:
            X_test = scaler.transform(test_df[FEATURE_COLUMNS].fillna(0).values)
            y_test = test_df["podium"].values
            y_pred = clf.predict(X_test)
            y_proba = clf.predict_proba(X_test)[:, 1]

            self._metrics = CrossRaceMetrics(
                accuracy=round(float(accuracy_score(y_test, y_pred)), 4),
                precision=round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
                recall=round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
                f1_score=round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
                roc_auc=round(float(roc_auc_score(y_test, y_proba)), 4),
                training_race_count=training_race_count,
                test_race_count=test_race_count,
            )
            self._circuit_accuracy = self._compute_circuit_accuracy(test_df, clf, scaler)
        else:
            # Fallback: training metrics
            y_pred_tr = clf.predict(X_train_scaled)
            y_proba_tr = clf.predict_proba(X_train_scaled)[:, 1]
            self._metrics = CrossRaceMetrics(
                accuracy=round(float(accuracy_score(y_train, y_pred_tr)), 4),
                precision=round(float(precision_score(y_train, y_pred_tr, zero_division=0)), 4),
                recall=round(float(recall_score(y_train, y_pred_tr, zero_division=0)), 4),
                f1_score=round(float(f1_score(y_train, y_pred_tr, zero_division=0)), 4),
                roc_auc=round(float(roc_auc_score(y_train, y_proba_tr)), 4),
                training_race_count=training_race_count,
                test_race_count=0,
            )
            self._circuit_accuracy = self._compute_circuit_accuracy(train_df, clf, scaler)

        self._trained = True
        logger.info(
            "CrossRaceModel trained. Train races: %d, Test races: %d, ROC-AUC: %.3f",
            training_race_count, test_race_count,
            self._metrics.roc_auc if self._metrics else 0,
        )

    def _compute_circuit_accuracy(self, df: pd.DataFrame, clf, scaler: StandardScaler) -> list[CircuitAccuracy]:
        results: list[CircuitAccuracy] = []
        if "circuit_name" not in df.columns:
            return results
        for circuit, group in df.groupby("circuit_name"):
            X = scaler.transform(group[FEATURE_COLUMNS].fillna(0).values)
            y_true = group["podium"].values
            y_pred = clf.predict(X)
            race_count = group["gp_slug"].nunique() if "gp_slug" in group.columns else len(group)
            results.append(CircuitAccuracy(
                circuit_name=str(circuit),
                precision=round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
                recall=round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
                race_count=race_count,
                low_sample_warning=race_count < 3,
            ))
        return results

    def predict_race(self, race_vectors: list[dict]) -> list[PodiumPredictionResult]:
        if not self._trained or self._clf is None or self._scaler is None:
            raise RuntimeError("Model is not trained yet.")

        predictions: list[PodiumPredictionResult] = []
        for vec in race_vectors:
            try:
                X_raw = np.array([[vec.get(col, 0) for col in FEATURE_COLUMNS]], dtype=float)
                X = self._scaler.transform(X_raw)
                prob = float(self._clf.predict_proba(X)[0][1])

                # CI from sub-estimators
                sub_probs = []
                try:
                    for _, est in self._clf.estimators:
                        p = float(est.predict_proba(X)[0][1])
                        sub_probs.append(p)
                except Exception:
                    sub_probs = [prob]

                ci_low = float(np.percentile(sub_probs, 10))
                ci_high = float(np.percentile(sub_probs, 90))

                predictions.append(PodiumPredictionResult(
                    driver_code=str(vec.get("driver_code", "")),
                    podium_probability=round(prob, 3),
                    ci_low=round(ci_low, 3),
                    ci_high=round(ci_high, 3),
                    above_threshold=prob > 0.5,
                    actual_podium=vec.get("actual_podium"),
                ))
            except Exception as exc:
                logger.warning("Prediction failed for %s: %s", vec.get("driver_code"), exc)

        predictions.sort(key=lambda p: p.podium_probability, reverse=True)
        return predictions

    def get_metrics(self) -> CrossRaceMetrics | None:
        return self._metrics

    def get_circuit_accuracy(self) -> list[CircuitAccuracy]:
        return self._circuit_accuracy

    def is_trained(self) -> bool:
        return self._trained


# Module-level singleton
cross_race_model = CrossRaceModel()
