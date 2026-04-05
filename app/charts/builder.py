"""ChartBuilder: converts F1 analysis data into Plotly figure dicts."""

from __future__ import annotations

import plotly.graph_objects as go

TYRES_COLOR_DICT = {
    "SOFT": "red",
    "MEDIUM": "#FFC000",
    "HARD": "white",
    "INTERMEDIATE": "green",
    "WET": "blue",
}


class ChartBuilder:
    """Converts F1 data structures into Plotly figure dicts (via .to_dict())."""

    def lap_time_distribution(self, fp2_df: list[dict]) -> dict:
        """Box plot per driver showing lap time distribution.

        Each trace has hover template showing lap number, lap time, tyre compound.
        """
        try:
            if not fp2_df:
                return {}

            # Group rows by driver
            drivers: dict[str, list[dict]] = {}
            for row in fp2_df:
                driver = row.get("Driver")
                if driver is None:
                    continue
                drivers.setdefault(driver, []).append(row)

            if not drivers:
                return {}

            fig = go.Figure()

            for driver, rows in drivers.items():
                lap_times = []
                lap_numbers = []
                compounds = []

                for row in rows:
                    lt = row.get("LapTime") or row.get("LapTimes")
                    ln = row.get("LapNumber") or row.get("LapNumbers")
                    compound = row.get("Compound", "UNKNOWN")

                    if lt is None:
                        continue

                    # LapTime may be a timedelta or a float (seconds)
                    if hasattr(lt, "total_seconds"):
                        lt = lt.total_seconds()
                    else:
                        try:
                            lt = float(lt)
                        except (TypeError, ValueError):
                            continue

                    lap_times.append(lt)
                    lap_numbers.append(ln)
                    compounds.append(compound)

                if not lap_times:
                    continue

                # Use the most common compound for box color
                compound_counts: dict[str, int] = {}
                for c in compounds:
                    compound_counts[c] = compound_counts.get(c, 0) + 1
                dominant_compound = max(compound_counts, key=lambda k: compound_counts[k])
                color = TYRES_COLOR_DICT.get(dominant_compound, "gray")

                # Custom data for hover
                custom_data = list(zip(lap_numbers, compounds))

                fig.add_trace(
                    go.Box(
                        y=lap_times,
                        name=driver,
                        marker_color=color,
                        customdata=custom_data,
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Lap: %{customdata[0]}<br>"
                            "Lap Time: %{y:.3f}s<br>"
                            "Compound: %{customdata[1]}<extra></extra>"
                        ),
                    )
                )

            fig.update_layout(title="FP2 Lap Time Distribution")
            return fig.to_dict()

        except Exception:
            return {}

    def stint_analysis(self, fp2_df: list[dict]) -> dict:
        """Bar chart showing average lap time per tyre compound per driver."""
        try:
            if not fp2_df:
                return {}

            # Aggregate: (driver, compound) -> list of lap times
            groups: dict[tuple[str, str], list[float]] = {}
            for row in fp2_df:
                driver = row.get("Driver")
                compound = row.get("Compound", "UNKNOWN")
                lt = row.get("LapTime") or row.get("LapTimes")

                if driver is None or lt is None:
                    continue

                if hasattr(lt, "total_seconds"):
                    lt = lt.total_seconds()
                else:
                    try:
                        lt = float(lt)
                    except (TypeError, ValueError):
                        continue

                key = (driver, compound)
                groups.setdefault(key, []).append(lt)

            if not groups:
                return {}

            # Build one trace per compound
            compounds_seen: set[str] = {k[1] for k in groups}
            drivers_seen: list[str] = sorted({k[0] for k in groups})

            fig = go.Figure()

            for compound in sorted(compounds_seen):
                avg_times = []
                for driver in drivers_seen:
                    times = groups.get((driver, compound), [])
                    avg_times.append(sum(times) / len(times) if times else None)

                color = TYRES_COLOR_DICT.get(compound, "gray")
                fig.add_trace(
                    go.Bar(
                        name=compound,
                        x=drivers_seen,
                        y=avg_times,
                        marker_color=color,
                    )
                )

            fig.update_layout(
                title="FP2 Stint Analysis - Average Lap Time by Compound",
                barmode="group",
            )
            return fig.to_dict()

        except Exception:
            return {}

    def qualifying_gap_to_pole(self, grid: list[dict]) -> dict:
        """Horizontal bar chart of gap to pole for each driver, sorted ascending."""
        try:
            if not grid:
                return {}

            # Accept both dict and GridEntry-like objects
            entries = []
            for item in grid:
                if isinstance(item, dict):
                    driver = item.get("driver_code")
                    best = item.get("best_lap_seconds")
                else:
                    driver = getattr(item, "driver_code", None)
                    best = getattr(item, "best_lap_seconds", None)

                if driver is None or best is None:
                    continue
                try:
                    entries.append((driver, float(best)))
                except (TypeError, ValueError):
                    continue

            if not entries:
                return {}

            min_time = min(t for _, t in entries)
            gaps = [(driver, round(t - min_time, 4)) for driver, t in entries]

            # Sort ascending by gap (pole at top when displayed as horizontal bar)
            gaps.sort(key=lambda x: x[1])

            drivers = [d for d, _ in gaps]
            gap_values = [g for _, g in gaps]

            fig = go.Figure(
                go.Bar(
                    x=gap_values,
                    y=drivers,
                    orientation="h",
                )
            )
            fig.update_layout(
                title="Qualifying Gap to Pole",
                xaxis_title="Gap (seconds)",
                yaxis_title="Driver",
            )
            return fig.to_dict()

        except Exception:
            return {}

    def teammate_comparison(self, grid: list[dict], teammate_pairs: dict) -> dict:
        """Bar chart with one bar per constructor pair showing qualifying delta (ms)."""
        try:
            if not grid or not teammate_pairs:
                return {}

            # Build driver -> best_lap_seconds map
            driver_times: dict[str, float] = {}
            for item in grid:
                if isinstance(item, dict):
                    driver = item.get("driver_code")
                    best = item.get("best_lap_seconds")
                else:
                    driver = getattr(item, "driver_code", None)
                    best = getattr(item, "best_lap_seconds", None)

                if driver is None or best is None:
                    continue
                try:
                    driver_times[driver] = float(best)
                except (TypeError, ValueError):
                    continue

            if not driver_times:
                return {}

            # Deduplicate pairs (avoid double-counting A-B and B-A)
            seen_pairs: set[frozenset] = set()
            pair_labels: list[str] = []
            deltas: list[float] = []

            for d1, d2 in teammate_pairs.items():
                pair_key = frozenset({d1, d2})
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                t1 = driver_times.get(d1)
                t2 = driver_times.get(d2)
                if t1 is None or t2 is None:
                    continue

                delta_ms = round((t1 - t2) * 1000, 1)
                pair_labels.append(f"{d1} vs {d2}")
                deltas.append(delta_ms)

            if not pair_labels:
                return {}

            fig = go.Figure(
                go.Bar(
                    x=pair_labels,
                    y=deltas,
                )
            )
            fig.update_layout(title="Teammate Qualifying Comparison (ms)")
            return fig.to_dict()

        except Exception:
            return {}

    def lap_by_lap_positions(self, sim_result: dict) -> dict:
        """Placeholder — use lap_by_lap_positions_from_data for real data."""
        return {}

    def lap_by_lap_positions_from_data(self, lap_positions: dict, laps: list) -> dict:
        """Line chart showing position per lap for each driver."""
        try:
            if not lap_positions:
                return {}
            fig = go.Figure()
            for driver, positions in lap_positions.items():
                fig.add_trace(go.Scatter(
                    x=laps,
                    y=positions,
                    mode="lines",
                    name=driver,
                    hovertemplate=f"<b>{driver}</b><br>Lap: %{{x}}<br>Position: %{{y}}<extra></extra>",
                ))
            fig.update_layout(
                title="Race Simulation - Lap by Lap Positions",
                xaxis_title="Lap",
                yaxis_title="Position",
                yaxis={"autorange": "reversed", "dtick": 1},
            )
            return fig.to_dict()
        except Exception:
            return {}

    def feature_importance(self, feature_importance: list[dict]) -> dict:
        """Horizontal bar chart of top-10 features sorted descending by importance."""
        try:
            if not feature_importance:
                return {}

            # Accept both dicts and FeatureScore-like objects
            scores: list[tuple[str, float]] = []
            for item in feature_importance:
                if isinstance(item, dict):
                    name = item.get("feature_name")
                    imp = item.get("importance")
                else:
                    name = getattr(item, "feature_name", None)
                    imp = getattr(item, "importance", None)

                if name is None or imp is None:
                    continue
                try:
                    scores.append((str(name), float(imp)))
                except (TypeError, ValueError):
                    continue

            if not scores:
                return {}

            # Sort descending, take top 10
            scores.sort(key=lambda x: x[1], reverse=True)
            top10 = scores[:10]

            # Reverse for horizontal bar so highest is at top
            top10_reversed = list(reversed(top10))
            names = [n for n, _ in top10_reversed]
            importances = [i for _, i in top10_reversed]

            fig = go.Figure(
                go.Bar(
                    x=importances,
                    y=names,
                    orientation="h",
                )
            )
            fig.update_layout(
                title="Feature Importance (Random Forest)",
                xaxis_title="Importance",
                yaxis_title="Feature",
            )
            return fig.to_dict()

        except Exception:
            return {}

    def podium_probability_chart(self, predictions: list[dict]) -> dict:
        """Horizontal bar chart of podium probabilities with CI error bars.

        Bars are colored green (#2ecc71) if above_threshold=True, gray (#888) otherwise.
        Sorted descending by probability.
        """
        try:
            if not predictions:
                return {}

            # Normalize to dicts
            rows = []
            for p in predictions:
                if isinstance(p, dict):
                    rows.append(p)
                else:
                    rows.append({
                        "driver_code": getattr(p, "driver_code", ""),
                        "podium_probability": getattr(p, "podium_probability", 0.0),
                        "ci_low": getattr(p, "ci_low", 0.0),
                        "ci_high": getattr(p, "ci_high", 0.0),
                        "above_threshold": getattr(p, "above_threshold", False),
                    })

            # Sort descending by probability
            rows.sort(key=lambda x: x.get("podium_probability", 0.0), reverse=True)

            drivers = [r["driver_code"] for r in rows]
            probs = [r["podium_probability"] for r in rows]
            ci_lows = [r["ci_low"] for r in rows]
            ci_highs = [r["ci_high"] for r in rows]
            colors = ["#2ecc71" if r.get("above_threshold") else "#888" for r in rows]

            # Error bar values: symmetric around prob using ci_low/ci_high
            error_minus = [max(0.0, p - lo) for p, lo in zip(probs, ci_lows)]
            error_plus = [max(0.0, hi - p) for p, hi in zip(probs, ci_highs)]

            fig = go.Figure(
                go.Bar(
                    x=probs,
                    y=drivers,
                    orientation="h",
                    marker_color=colors,
                    error_x=dict(
                        type="data",
                        symmetric=False,
                        array=error_plus,
                        arrayminus=error_minus,
                    ),
                    customdata=list(zip(ci_lows, ci_highs)),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Probability: %{x:.1%}<br>"
                        "CI: [%{customdata[0]:.1%}, %{customdata[1]:.1%}]"
                        "<extra></extra>"
                    ),
                )
            )
            fig.update_layout(
                title="Podium Probability Prediction",
                xaxis_title="Probability",
                yaxis_title="Driver",
            )
            return fig.to_dict()

        except Exception:
            return {}

    def circuit_accuracy_chart(self, circuit_accuracy: list[dict]) -> dict:
        """Grouped bar chart of precision and recall per circuit.

        Adds '⚠ Low sample' annotation for circuits with low_sample_warning=True.
        """
        try:
            if not circuit_accuracy:
                return {}

            rows = []
            for c in circuit_accuracy:
                if isinstance(c, dict):
                    rows.append(c)
                else:
                    rows.append({
                        "circuit_name": getattr(c, "circuit_name", ""),
                        "precision": getattr(c, "precision", 0.0),
                        "recall": getattr(c, "recall", 0.0),
                        "race_count": getattr(c, "race_count", 0),
                        "low_sample_warning": getattr(c, "low_sample_warning", False),
                    })

            circuit_names = [r["circuit_name"] for r in rows]
            precisions = [r["precision"] for r in rows]
            recalls = [r["recall"] for r in rows]

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name="Precision",
                    x=circuit_names,
                    y=precisions,
                    marker_color="blue",
                    hovertemplate="<b>%{x}</b><br>Precision: %{y:.1%}<extra></extra>",
                )
            )
            fig.add_trace(
                go.Bar(
                    name="Recall",
                    x=circuit_names,
                    y=recalls,
                    marker_color="orange",
                    hovertemplate="<b>%{x}</b><br>Recall: %{y:.1%}<extra></extra>",
                )
            )

            # Annotations for low-sample circuits
            annotations = []
            for i, r in enumerate(rows):
                if r.get("low_sample_warning"):
                    annotations.append(dict(
                        x=r["circuit_name"],
                        y=max(r["precision"], r["recall"]) + 0.05,
                        text="⚠ Low sample",
                        showarrow=False,
                        font=dict(size=10, color="orange"),
                    ))

            fig.update_layout(
                title="Circuit Accuracy (Test Set)",
                barmode="group",
                annotations=annotations,
            )
            return fig.to_dict()

        except Exception:
            return {}

    def model_metrics_chart(self, metrics: dict) -> dict:
        """Bar chart showing all 5 model performance metrics."""
        try:
            if not metrics:
                return {}

            if not isinstance(metrics, dict):
                metrics = {
                    "accuracy": getattr(metrics, "accuracy", 0.0),
                    "precision": getattr(metrics, "precision", 0.0),
                    "recall": getattr(metrics, "recall", 0.0),
                    "f1_score": getattr(metrics, "f1_score", 0.0),
                    "roc_auc": getattr(metrics, "roc_auc", 0.0),
                }

            metric_names = ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"]
            metric_keys = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
            values = [metrics.get(k, 0.0) for k in metric_keys]

            fig = go.Figure(
                go.Bar(
                    x=metric_names,
                    y=values,
                    hovertemplate="<b>%{x}</b><br>Value: %{y:.1%}<extra></extra>",
                )
            )
            fig.update_layout(
                title="Model Performance Metrics (Test Set)",
                yaxis_title="Score",
                yaxis=dict(range=[0, 1]),
            )
            return fig.to_dict()

        except Exception:
            return {}
