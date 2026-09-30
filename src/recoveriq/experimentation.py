from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.stats import chisquare
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


@dataclass(frozen=True)
class ExperimentPlan:
    baseline_rate: float
    absolute_mde: float
    alpha: float
    power: float
    allocation_treatment: float
    sample_per_arm: int
    total_sample: int
    estimated_days: int | None


def sample_size_plan(
    baseline_rate: float,
    absolute_mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
    allocation_treatment: float = 0.50,
    eligible_customers_per_day: int | None = None,
) -> ExperimentPlan:
    if not 0 < baseline_rate < 1 or not 0 < baseline_rate + absolute_mde < 1:
        raise ValueError("Baseline and baseline + MDE must be probabilities between 0 and 1.")
    if not 0 < allocation_treatment < 1:
        raise ValueError("Treatment allocation must be between 0 and 1.")
    effect = abs(proportion_effectsize(baseline_rate + absolute_mde, baseline_rate))
    ratio = allocation_treatment / (1 - allocation_treatment)
    control_n = math.ceil(NormalIndPower().solve_power(effect, power=power, alpha=alpha, ratio=ratio))
    treatment_n = math.ceil(control_n * ratio)
    total = control_n + treatment_n
    days = math.ceil(total / eligible_customers_per_day) if eligible_customers_per_day else None
    return ExperimentPlan(baseline_rate, absolute_mde, alpha, power, allocation_treatment, max(control_n, treatment_n), total, days)


def srm_test(control_n: int, treatment_n: int, expected_treatment_share: float = 0.5) -> dict[str, float | bool]:
    observed = np.array([control_n, treatment_n])
    expected = observed.sum() * np.array([1 - expected_treatment_share, expected_treatment_share])
    statistic, p_value = chisquare(observed, expected)
    return {"chi_square": float(statistic), "p_value": float(p_value), "srm_flag": bool(p_value < 0.001)}


def policy_simulation(
    scored_orders: pd.DataFrame,
    budget: float,
    offer_cost: float,
    assumed_retention_lift: float,
    retained_customer_value: float,
) -> dict[str, float | int]:
    if budget < 0 or offer_cost <= 0 or not 0 <= assumed_retention_lift <= 1:
        raise ValueError("Budget/cost/lift inputs are outside valid ranges.")
    eligible = scored_orders.sort_values("late_probability", ascending=False).copy()
    selected_n = min(len(eligible), int(budget // offer_cost))
    selected = eligible.head(selected_n)
    expected_incremental_retained = float(
        (selected.late_probability * assumed_retention_lift).sum()
    )
    spend = selected_n * offer_cost
    expected_value = expected_incremental_retained * retained_customer_value
    break_even_lift = (
        spend / (retained_customer_value * selected.late_probability.sum())
        if selected_n and retained_customer_value > 0
        else float("inf")
    )
    return {
        "selected_orders": selected_n,
        "spend": float(spend),
        "expected_incremental_retained": expected_incremental_retained,
        "expected_value": expected_value,
        "expected_net_value": float(expected_value - spend),
        "expected_roi": float((expected_value - spend) / spend) if spend else 0.0,
        "break_even_lift": float(break_even_lift),
    }


def mde_grid(baseline_rate: float, eligible_customers_per_day: int = 1000) -> pd.DataFrame:
    rows = []
    for mde in [0.005, 0.01, 0.015, 0.02]:
        rows.append(asdict(sample_size_plan(baseline_rate, mde, eligible_customers_per_day=eligible_customers_per_day)))
    return pd.DataFrame(rows)
