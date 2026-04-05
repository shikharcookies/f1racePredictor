"""
Contains constants for analysing a Formula 1 weekend.
"""
import fastf1 as ff1
import matplotlib.patches as mpatches
# Enable the cache by providing the name of the cache folder
ff1.Cache.enable_cache('cache')

# Constants for tyre strings
SOFT = 'SOFT'
MEDIUM = 'MEDIUM'
HARD = 'HARD'
INTERMEDIATE = 'INTERMEDIATE'
WET = 'WET'
DRY_TYRES = [SOFT, MEDIUM, HARD]
WET_TYRES = [INTERMEDIATE, WET]

# Set the mapping for plot legend labels
SOFT_PATCHES = mpatches.Patch(color='red', label='Soft')
MEDIUM_PATCHES = mpatches.Patch(color='yellow', label='Medium')
HARD_PATCHES = mpatches.Patch(color='white', label='Hard')
INTERMEDIATE_PATCHES = mpatches.Patch(color='green', label='Intermediate')
WET_PATCHES = mpatches.Patch(color='blue', label='Wet')
TYRES_COLOR_LEGEND = [SOFT_PATCHES, MEDIUM_PATCHES, HARD_PATCHES, INTERMEDIATE_PATCHES, WET_PATCHES]

# Another color mapping... just for the purpose of line plot
TYRES_COLOR_DICT = {"SOFT": "red", "MEDIUM": "#FFC000", "HARD": "white", "INTERMEDIATE": "green",
                    "WET": "blue"}

TYRE_DEGRADATION_REGRESSION_DEGREE = 2

QUALIFYING_SESSIONS = ['Q1', 'Q2', 'Q3']

# Teammate pairs in 2022 and values can be keys
TEAMMATE_PAIRS_DICT = {'RUS': 'HAM', 'VER': 'PER', 'MSC': 'MAG', 'BOT': 'ZHO', 'RIC': 'NOR',
                       'STR': 'VET', 'ALB': 'LAT', 'TSU': 'GAS', 'OCO': 'ALO', 'SAI': 'LEC'}
TEAMMATE_PAIRS_DICT.update({v: k for k, v in TEAMMATE_PAIRS_DICT.items()})

# Constants for determining driver performance
TEAMMATE_MAX_GAP_SECOND = 1
QUALIFYING_MAX_GAP_PERCENTAGE = 1.02
FP2_MAX_GAP_PERCENTAGE = 1.03
MAX_GAP_VALUE = 20
