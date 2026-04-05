"""
Contains helper functions for analysing race data in notebook.
"""
import fastf1 as ff1
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from constants import *
from scipy import stats
import matplotlib.patches as mpatches

# Enable the cache by providing the name of the cache folder
from race import convert_laptime_to_seconds, get_all_driver_names
ff1.Cache.enable_cache('cache')


def remove_outlier_laps(df):
    df.loc[(np.abs(stats.zscore(df.LapTime)) >= 1), "LapTime"] = np.NaN


def get_tyre_model(df):
    # Plot a best fit line
    # Only consider the indices where both x and y are not missing
    valid_indices = np.isfinite(df.TyreLife) & np.isfinite(df.LapTime)

    # Only returns a model if valid
    # i.e. expect a non-empty vector for x
    if valid_indices.size > 0:
        return np.poly1d(np.polyfit(df.TyreLife[valid_indices], df.LapTime[valid_indices],
                                    TYRE_DEGRADATION_REGRESSION_DEGREE))

    return None


def plot_tyre_model(df, model=None, axes=None, size=None, row=0, column=0, color='#1f77b4',
                    remove_outlier=True):
    # Get the range of the regression line wanted
    m = df.TyreLife.min()
    M = df.TyreLife.max()

    if size[0] == 1:
        axs = axes[column]
    else:
        axs = axes[row, column]

    if remove_outlier:
        outlier_indices = np.abs(stats.zscore(df.LapTime)) >= 1
    else:
        outlier_indices = np.zeros(df.shape[0], dtype=bool)

    if axes is not None:
        subplot = df[~outlier_indices].plot(kind='scatter', x='TyreLife', y='LapTime',
                                            title=df['Driver'].unique().tolist()[0],
                                            ax=axs,
                                            figsize=(25, 18), color=color)
        subplot = df[outlier_indices].plot(kind='scatter', x='TyreLife', y='LapTime',
                                           title=df['Driver'].unique().tolist()[0],
                                           ax=axs,
                                           figsize=(25, 18), color='red')
        # Plot the line
        if model is not None:
            # The third parameter is the number of samples, set it to double of the laps
            polyline = np.linspace(m, M, int((M - m) * 2))
            axs.plot(polyline, model(polyline))
    else:
        subplot = df[~outlier_indices].plot(kind='scatter', x='TyreLife', y='LapTime',
                                            title=df['Driver'].unique().tolist()[0], color=color)
        subplot = df[outlier_indices].plot(kind='scatter', x='TyreLife', y='LapTime',
                                           title=df['Driver'].unique().tolist()[0], color='red')
        # Plot the line
        if model is not None:
            # The third parameter is the number of samples, set it to double of the laps
            polyline = np.linspace(m, M, int((M - m) * 2))
            plt.plot(polyline, model(polyline))

    return subplot


def get_number_of_valid_laps(df):
    return df.loc[df['LapTime'].notnull()].shape[0]


def plot_dry_tyre_models_all_drivers(df, drivers):
    # Make a subplot
    fig, axs = plt.subplots(len(drivers), 3)
    fig.suptitle('Long Run Race Pace')

    for i in range(len(drivers)):
        for j in range(len(DRY_TYRES)):
            # Only pick representative laps - laps that are set under green flag and not in/out laps
            rep_laps = df.pick_driver(drivers[i]).pick_accurate().pick_wo_box().pick_track_status(
                '1')

            # Convert laptime from timedelta to seconds for plotting
            convert_laptime_to_seconds(rep_laps)

            rep_laps_by_tyre = rep_laps.pick_tyre(DRY_TYRES[j])

            if get_number_of_valid_laps(rep_laps_by_tyre) > 4:
                remove_outlier_laps(rep_laps_by_tyre)

            if get_number_of_valid_laps(rep_laps_by_tyre) > 3:

                model = get_tyre_model(rep_laps_by_tyre)
                plot_tyre_model(rep_laps.pick_tyre(DRY_TYRES[j]), model=model, axes=axs,
                                size=(len(drivers), 3), row=i, column=j)

            elif get_number_of_valid_laps(rep_laps_by_tyre) > 0:
                plot_tyre_model(rep_laps.pick_tyre(DRY_TYRES[j]), None, axs, (len(drivers), 3), i,
                                j, 'red', False)

            else:
                if len(drivers) == 1:
                    axs[j].title.set_text(drivers[i])
                else:
                    axs[i, j].title.set_text(drivers[i])


def extract_long_run_pace_from_longest_practice_stint(df, driver):
    """Extract the long run race pace from the longest stint in FP2.

    df: FP2.laps
    driver: String of the driver initials
    """
    df = df.pick_driver(driver).pick_accurate()

    stints = []
    longest_stint_tyrelife_df = []
    longest_stint_index = -1
    longest_stint_length = -1

    for i in df.Stint.unique():
        current_stint = df.loc[df.Stint == i]
        stints.append(current_stint)

        # Find longest stint
        # We pick the later stint as reference if two are the same length.
        current_stint_length = current_stint.shape[0]
        if longest_stint_length <= current_stint.shape[0]:
            longest_stint_index = len(stints) - 1
            longest_stint_length = current_stint_length
            longest_stint_tyrelife_df = df[df['Stint'] == i].TyreLife.tolist()

    longest_stint_df = stints[longest_stint_index].copy()
    convert_laptime_to_seconds(longest_stint_df)

    longest_stint_laptime_df = longest_stint_df['LapTime']
    longest_stint_laptime_diff_df = longest_stint_laptime_df.diff()

    while sum(longest_stint_laptime_diff_df.loc[abs(longest_stint_laptime_df.diff()) > 1]) > 0:
        smallest_index = \
            longest_stint_laptime_diff_df.loc[abs(longest_stint_laptime_df.diff()) > 1].index[0]

        time_delta = longest_stint_laptime_diff_df.loc[smallest_index]
        if time_delta > 0:
            longest_stint_tyrelife_df.pop(longest_stint_laptime_df.index.get_loc(smallest_index))
            longest_stint_laptime_df.drop(smallest_index, inplace=True)
        else:
            # Since the indices are not continuous, smallest_index - 1 may be invalid.
            # e.g. longest_stint_laptime_df.drop(smallest_index - 1, inplace=True) does NOT work.
            # longest_stint_laptime_diff_df.drop(smallest_index - 1, inplace=True)
            # In this case, split the dataframe and reconstruct it.

            # Since we are using slicing operation here, we cannot use smallest_index directly since
            # smallest_index is the index of the row, but not the row number, which is used for
            # slicing. Instead we can do the following:
            wanted_index = longest_stint_laptime_df.index.get_loc(smallest_index)
            longest_stint_laptime_df_upper_half = longest_stint_laptime_df.iloc[:wanted_index]
            longest_stint_laptime_df_lower_half = longest_stint_laptime_df.iloc[wanted_index:]

            # Drop the last row of the upper half, which holds the slower lap
            longest_stint_laptime_df_upper_half = longest_stint_laptime_df_upper_half[:-1]

            longest_stint_laptime_df = pd.concat([longest_stint_laptime_df_upper_half,
                                                  longest_stint_laptime_df_lower_half])

            longest_stint_tyrelife_df.pop(longest_stint_laptime_df.index.get_loc(smallest_index))

        longest_stint_laptime_diff_df = longest_stint_laptime_df.diff()

    return (longest_stint_laptime_df.tolist(), longest_stint_df.Compound.unique()[0], longest_stint_tyrelife_df)
