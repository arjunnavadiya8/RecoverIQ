import pytest

from recoveriq.experimentation import policy_simulation, sample_size_plan, srm_test


def test_sample_size_decreases_for_larger_effect():
    small = sample_size_plan(0.10, 0.005)
    large = sample_size_plan(0.10, 0.02)
    assert small.total_sample > large.total_sample
    assert small.total_sample > 0


def test_srm_flags_large_imbalance():
    assert srm_test(1000, 1000)["srm_flag"] is False
    assert srm_test(1500, 500)["srm_flag"] is True


def test_policy_simulation_budget_and_labels():
    import pandas as pd

    result = policy_simulation(
        pd.DataFrame({"late_probability": [0.9, 0.6, 0.1]}),
        budget=20,
        offer_cost=10,
        assumed_retention_lift=0.02,
        retained_customer_value=500,
    )
    assert result["selected_orders"] == 2
    assert result["spend"] == 20
    assert result["expected_incremental_retained"] == pytest.approx(0.03)


def test_invalid_probability_inputs_fail():
    with pytest.raises(ValueError):
        sample_size_plan(1.1, 0.01)

