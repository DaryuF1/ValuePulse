import math


def poisson_probability(expected_goals, actual_goals):
    # Basic Poisson probability formula for exact goal counts
    return ((expected_goals ** actual_goals) * math.exp(-expected_goals)) / math.factorial(actual_goals)


def calculate_1x2_probs(home_xg, away_xg):
    # Loop through score lines up to 5 goals to aggregate 1X2 outcomes
    prob_1 = 0.0
    prob_X = 0.0
    prob_2 = 0.0

    for home_goals in range(6):
        for away_goals in range(6):
            prob_score = (poisson_probability(home_xg, home_goals) *
                          poisson_probability(away_xg, away_goals))

            if home_goals > away_goals:
                prob_1 += prob_score
            elif home_goals == away_goals:
                prob_X += prob_score
            else:
                prob_2 += prob_score

    return {
        '1': prob_1,
        'X': prob_X,
        '2': prob_2
    }


if __name__ == "__main__":
    # Quick standalone sanity check test
    meci_test_home_xg = 1.8
    meci_test_away_xg = 1.2

    sanse = calculate_1x2_probs(meci_test_home_xg, meci_test_away_xg)

    print(f"Calculated probabilities for an xG of {meci_test_home_xg} - {meci_test_away_xg}:")
    print(f"Home win chance (1): {sanse['1'] * 100:.1f}%")
    print(f"Draw chance (X):     {sanse['X'] * 100:.1f}%")
    print(f"Away win chance (2): {sanse['2'] * 100:.1f}%")