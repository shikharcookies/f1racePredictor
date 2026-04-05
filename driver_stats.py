"""
Contains helper functions for analysing drivers' career performance.
"""


def get_stint_lengths(stints_list: list):
    """
    Calculate the stint length for each stint based on a sequence of tyres used in each lap.

    :param stints_list: a list containing strings in {SOFT, MEDIUM, HARD, INTERMEDIATE, WET}
    :return: a list of tuples containing the tyre compound and the length of stints.
    E.g. [('SOFT', 3), ('HARD', 2)]
    """

    # Returns an empty list if input is empty
    if stints_list == []:
        return []

    # The final result
    stints_tuples = []

    # Variables for tracking the stint in the for loop below.
    stint_laps = 0
    curr = None

    for i in range(len(stints_list)):
        curr = stints_list[i]
        # For the first stint, start counting the laps on this current stint.
        if i == 0:
            stint_laps = 1
        else:
            stint_laps += 1
            prev = stints_list[i - 1]
            # If the current stint is different from the previous one, this means the driver
            # has changed a tyres and we can conclude the previous stint lap count.
            if curr != prev:
                stints_tuples.append((prev, stint_laps - 1))
                stint_laps = 1

    # For the final stint, remember to append the result to the returning list.
    stints_tuples.append((curr, stint_laps))

    return stints_tuples
