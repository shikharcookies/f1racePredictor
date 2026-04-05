"""
Contains helper functions for analysing qualifying data in notebook.
"""
import pandas as pd

from constants import *
# Enable the cache by providing the name of the cache folder
ff1.Cache.enable_cache('cache')


def get_fastest_lap_in_qualifying(df) -> object:
    """
    Returns a dataframe summarizing the fastest laps of each driver in Q1, Q2, Q3 and overall.

    :param df: a numpy.DataFrame object (or more precisely, a fastf1.core.SessionResults object)
    :return: a numpy.DataFrame object containing the drivers' best times in each qualifying rounds.
    """

    # Create a pandas DataFrame for saving the best time laps.
    times_df = pd.DataFrame(df.Abbreviation)

    # For each qualifying sessions (Q1, Q2, Q3),
    for q in QUALIFYING_SESSIONS:
        # Change the lap time of the drivers to seconds.
        df.loc[:, q] = df[q].dt.total_seconds()
        # Add the times columns to times_df
        times_df = pd.concat([times_df, df[q]], axis=1)

    # Add a column containing the fastest lap for each driver across the whole qualifying.
    times_df['Fastest Lap'] = times_df[QUALIFYING_SESSIONS].min(axis=1)

    return times_df
