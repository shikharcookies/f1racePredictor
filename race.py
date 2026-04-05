"""
Contains helper functions for analysing race data in notebook.
"""
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from constants import *
# Enable the cache by providing the name of the cache folder
ff1.Cache.enable_cache('cache')


def get_all_driver_names(df) -> list:
    """
    Returns a list of drivers in a race session.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object

    :return: a list of strings which are the abbreviations of the drivers in the race session.
    """
    return df['Driver'].unique().tolist()


def calculate_race_lap_times(df) -> None:
    """
    Calculates the lap times of null lap times. Most common case of a null lap time is the first
    lap of a race.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object
    """
    # Get the indices of rows whose "LapTime" is null
    null_lap_time_indices = df.index[pd.isnull(df["LapTime"])].tolist()

    # The LapTime is calculated to be
    # the difference of the start time of the next lap and the current lap.
    for i in null_lap_time_indices:
        df.loc[i, "LapTime"] = df.loc[i + 1, "LapStartTime"] - df.loc[i, "LapStartTime"]


def convert_laptime_to_seconds(df) -> None:
    """
    Converts lap times from TimeDelta object to seconds (floats) in place.

    This method can only be called when the lap times in the dataframe (the 'LapTime' column)
    are in the form of TimeDelta. Otherwise an error will be thrown.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object
    """
    # Ignore warning: A value is trying to be set on a copy of a slice from a DataFrame.
    df.loc[:, "LapTime"] = df["LapTime"].dt.total_seconds()


def get_track_status_by_lap(df) -> list:
    """
    Returns a list of strings indicating track statuses.

    Note that several track statuses can occur at the same time and during the same lap.

    TODO: Update the representation of track status, e.g. Safety Car Ending, Restarts etc.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object
    :return: A list (whose length is the same as number of laps of the race) of strings. The string
    represents the track condition of the (index + 1) lap.
    """

    # The result list
    track_status = []

    # Iterate the 'TrackStatus' column of df and translate the number codes to strings
    for status in df["TrackStatus"]:
        if '4' in str(status):
            track_status.append("Safety Car Deployed")
        elif '7' in str(status):
            track_status.append("VSC Ending")
        elif '6' in str(status):
            track_status.append("VSC Deployed")
        elif '5' in str(status):
            track_status.append("Red Flag")
        else:
            track_status.append("")

    return track_status


def plot_lap_time_bar_graph(df) -> object:
    """
    Returns (and shows) the bar plot showing the lap times against lap numbers of one driver.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object
    :return: A subplot of a driver
    """
    subplot = df.plot(kind='bar', x='LapNumber', y='LapTime',
                      ylabel='Lap Time (second)', xlabel='Lap Number',
                      figsize=(20, 10), xticks=np.arange(0, 71, step=5),
                      width=0.99, edgecolor="black",
                      color=df["Compound"].map({'SOFT': "red", "MEDIUM": "yellow", "HARD": "white"})
                      )

    # Add a custom legend

    plt.legend(handles=TYRES_COLOR_LEGEND, loc="upper right")
    # Add custom text indicating track status
    track_status = get_track_status_by_lap(df)
    for bar, lap_status in zip(subplot.patches, track_status):
        subplot.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_width(), lap_status,
                     color="black", rotation="vertical")

    # Return and show the plot.
    return subplot


def plot_lap_time_line_graph(df) -> object:
    """
    Returns (and shows) the line plot showing the lap times against lap numbers of one driver.

    :param df: A DataFrame containing data of a race session. Usually this is a fastf1.core.Laps
    object
    :return: A subplot of a driver
    """
    temp_df = df.copy().set_index("Compound", append=True).unstack("Compound")["LapTime"]

    subplot = temp_df.plot(color=TYRES_COLOR_DICT, ylabel='Lap Time (second)',
                           xlabel='Lap Number', figsize=(20, 10))

    # Add a custom legend
    plt.legend(handles=TYRES_COLOR_LEGEND, loc="upper right")

    # Return and show the plot.
    return subplot
