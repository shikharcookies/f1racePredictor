"""
Contains helper functions for predicting race strategies.
"""
import fastf1 as ff1
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from constants import *
import matplotlib.patches as mpatches
# Enable the cache by providing the name of the cache folder
from race_sim import laptime_model
ff1.Cache.enable_cache('cache')

trackwear = 10

def get_head_to_head_df(fp2_df, quali_df):
    QUALIFYING_MIN_LAPTIME = quali_df['Fastest Lap'].min()

    FP2_MIN_MEDIAN_LAPTIME = fp2_df['MeanLapTime'].median()

    teammates_h2h = pd.DataFrame(
        columns=['Driver', 'GoodFP2', 'GoodQualifying', 'Teammate', 'FP2MeanLapTime',
                 'TeammateFP2MeanLapTime',
                 'QualifyingLapTime', 'TeammateQualifyingLapTime', 'QualifyingPosition',
                 'TeammateQualifyingPosition'])

    # To be inserted into teammates_h2h
    # Insert data into the h2h table
    for driver in TEAMMATE_PAIRS_DICT.keys():
        teammate = TEAMMATE_PAIRS_DICT[driver]

        # ".values[0]" extracts the values from the series/dataframe and index 0 extracts the first value, which should be the sole value.

        # FP2
        fp2_mean_laptime = fp2_df.loc[fp2_df['Driver'] == driver, 'MeanLapTime'].values[
            0]
        teammate_fp2_mean_laptime = \
        fp2_df.loc[fp2_df['Driver'] == teammate, 'MeanLapTime'].values[0]
        fp2_longest_stint_laps = len(
            fp2_df.loc[fp2_df['Driver'] == driver, 'LapNumbers'].values[0])

        # Qualifying
        q_fastest_lap = quali_df.loc[quali_df['Abbreviation'] == driver, 'Fastest Lap'].values[0]
        teammate_q_fastest_lap = \
        quali_df.loc[quali_df['Abbreviation'] == teammate, 'Fastest Lap'].values[0]
        q_position = quali_df.index.get_loc(
            quali_df[quali_df['Abbreviation'] == driver].index[0]) + 1
        teammate_q_position = quali_df.index.get_loc(
            quali_df[quali_df['Abbreviation'] == teammate].index[0]) + 1

        # Booleans of whether driver has a good qualifying and fp2 sim compared to his teammate
        good_qualifying = q_fastest_lap - teammate_q_fastest_lap < TEAMMATE_MAX_GAP_SECOND \
                          and q_fastest_lap < QUALIFYING_MIN_LAPTIME * QUALIFYING_MAX_GAP_PERCENTAGE

        good_fp2 = fp2_mean_laptime - teammate_fp2_mean_laptime < TEAMMATE_MAX_GAP_SECOND \
                   and fp2_mean_laptime < FP2_MIN_MEDIAN_LAPTIME * FP2_MAX_GAP_PERCENTAGE and fp2_longest_stint_laps >= 3

        teammates_h2h.loc[len(teammates_h2h)] = [driver, good_fp2, good_qualifying, teammate,
                                                 fp2_mean_laptime, teammate_fp2_mean_laptime,
                                                 q_fastest_lap, teammate_q_fastest_lap,
                                                 q_position, teammate_q_position]

    teammates_h2h = teammates_h2h.round(
        {'FP2MeanLapTime': 3, 'TeammateFP2MeanLapTime': 3}).sort_values(
        'QualifyingPosition').reset_index(drop=True)


    # Calculate Base Time
    for driver in TEAMMATE_PAIRS_DICT.keys():

        laptimes = fp2_df[fp2_df['Driver'] == driver].LapTimes.tolist()[0]
        laps = fp2_df[fp2_df['Driver'] == driver].LapNumbers.tolist()[0]
        laptimes = np.array(laptimes)
        laps = np.array(laps)

        if len(laps) > 2:
            # TODO: check parameters when function is refined.
            popt, pcov, model = laptime_model(laps, laptimes, MEDIUM)
            teammates_h2h.loc[teammates_h2h['Driver'] == driver, 'BaseTime'] = popt[0]
        else:
            teammates_h2h.loc[teammates_h2h['Driver'] == driver, 'BaseTime'] = 10000

    teammates_h2h = teammates_h2h.sort_values('BaseTime').reset_index(drop=True)


    # Calculate the long run estimate
    for driver in TEAMMATE_PAIRS_DICT.keys():
        self_row = teammates_h2h[teammates_h2h['Driver'] == driver]

        # Qualifying
        self_q_time = float(self_row.QualifyingLapTime)
        min_q_time = min(teammates_h2h.QualifyingLapTime)
        quali_gap = min(self_q_time - min_q_time, MAX_GAP_VALUE)

        # FP2
        self_fp2_time = float(self_row.BaseTime)
        min_fp2_time = min(teammates_h2h.BaseTime)

        fp2_gap = min(self_fp2_time - min_fp2_time, MAX_GAP_VALUE)

        good_fp2 = self_row.GoodFP2.iloc[0]
        good_quali = self_row.GoodQualifying.iloc[0]
        if good_fp2 or good_quali:
            teammates_h2h.loc[teammates_h2h['Driver'] == driver, 'LongRunEstimate'] = \
                min(teammates_h2h.BaseTime) + good_fp2 * (
                            1 - 0.5 * good_quali) * fp2_gap + good_quali * (
                            1 - 0.5 * good_fp2) * quali_gap
        else:
            teammate_row = teammates_h2h[teammates_h2h['Driver'] == TEAMMATE_PAIRS_DICT[driver]]
            fp2_gap = min(float(teammate_row.BaseTime) - min_fp2_time + 1, MAX_GAP_VALUE)
            quali_gap = min(float(teammate_row.BaseTime) - min_q_time + 1, MAX_GAP_VALUE)
            teammates_h2h.loc[teammates_h2h['Driver'] == driver, 'LongRunEstimate'] = \
                min(teammates_h2h.BaseTime) + (
                            1 - 0.5 * (quali_gap < 10)) * fp2_gap + good_quali * (
                            1 - 0.5 * (fp2_gap < 10)) * quali_gap

    teammates_h2h = teammates_h2h.sort_values('LongRunEstimate').reset_index(drop=True)

    return teammates_h2h
