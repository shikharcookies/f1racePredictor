"""
Contains helper functions for race simulation.
"""


from scipy.optimize import curve_fit

from practice import *

# Enable the cache by providing the name of the cache folder
ff1.Cache.enable_cache('cache')


def tyre_degradation_model(tyre_life: any, compound: str, deg_factor: float = 1) -> object:
    """
    A simple tyre degradation model.

    :param tyre_life: a number (int) representing the tyre life
    of the tyre compound or a numpy.array containing an array of (consecutive) integers
    representing the tyre life of the tyre compound

    :param compound: a string representing a tyre compound. Must be defined in constants.py, e.g.
    SOFT ('SOFT'), MEDIUM ('MEDIUM') etc.

    :param deg_factor: A float indicating the tyre degradation factor of the driver. The degradation
    rate is inversely proportional to the deg_factor, as seen in the first line of code below.
    A driver with a larger deg_factor has a better tyre management skill, thus can drive longer on
    a stint without losing much time.

    :return: a float or a numpy.array containing floats representing the time loss (or gain) based
    on the condition of the tyre.
    """

    # A larger deg_factor results in a smaller tyre_life, thus a driver with a larger
    # deg_factor can drive an older set of compounds faster compared to a driver with a smaller
    # deg_factor
    tyre_life = tyre_life / deg_factor

    # Simple tyre models with different dry compounds
    if compound == SOFT:
        return 0.0025 * tyre_life ** 2 + 0.05 * tyre_life - 1.5
    elif compound == MEDIUM:
        return 0.0008333 * tyre_life ** 2 + 0.01 * tyre_life - 0.4
    else:
        return 0.00007 * tyre_life ** 2 + 0.01 * tyre_life + 0


def laptime_model(lap_numbers: object, lap_times: object, compound: str) -> object:
    """
    Use a non-linear least squares method to fit the relationship between lap times and lap
    numbers (tyre life), according to a tyre_degradation_model.

    :param lap_numbers: a numpy.array containing the lap numbers the current tyre is on (
    equivalent to tyre life). Each lap number corresponds to a lap time in lap_times. (See
    below.)

    :param lap_times: a numpy.array containing the lap times. Each lap time corresponds
    to a lap_number in lap_numbers. (See above.)

    :param compound: a string representing a tyre compound. Must be defined in constants.py, e.g.
    SOFT ('SOFT'), MEDIUM ('MEDIUM') etc.

    :return: a tuple containing popt, the optimal values for the parameters; pcov, the estimated
    covariance of popt; and tyre_degradation_model, the function handler used for fitting the model.
    """

    def tyre_degradation_model_beta(tyre_life: object, beta: object) -> object:
        """

        :param tyre_life:
        :param beta: the random difference
        :return:
        """
        return tyre_degradation_model(tyre_life, compound) + beta

    popt, pcov = curve_fit(tyre_degradation_model_beta, lap_numbers, lap_times)

    return (popt, pcov, tyre_degradation_model)
