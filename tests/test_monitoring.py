import pandas as pd

from recoveriq.monitoring import population_stability_index


def test_psi_is_zero_for_identical_data():
    values = pd.Series(range(100))
    assert population_stability_index(values, values) == 0.0


def test_psi_detects_shift():
    reference = pd.Series(range(100))
    shifted = pd.Series(range(100, 200))
    assert population_stability_index(reference, shifted) > 0.2

