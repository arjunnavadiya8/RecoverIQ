import numpy as np
import pandas as pd

from recoveriq.config import FEATURE_COLUMNS
from recoveriq.modeling import chronological_split, classification_metrics


def test_feature_contract_excludes_post_outcome_fields():
    forbidden = {
        "order_delivered_customer_date",
        "review_score",
        "late_delivery",
        "low_review",
        "repeat_purchase_90d",
    }
    assert forbidden.isdisjoint(FEATURE_COLUMNS)


def test_chronological_split_is_ordered_and_complete():
    frame = pd.DataFrame(
        {
            "order_id": [f"o{i}" for i in range(100)],
            "order_purchase_timestamp": pd.date_range("2020-01-01", periods=100),
        }
    )
    split = chronological_split(frame)
    assert list(split.value_counts().sort_index()) == [15, 70, 15]
    assert set(split.iloc[:70]) == {"train"}
    assert set(split.iloc[-15:]) == {"test"}


def test_classification_metrics_include_decision_measure():
    y = pd.Series([0, 0, 1, 1])
    probability = np.array([0.1, 0.3, 0.7, 0.9])
    metrics = classification_metrics(y, probability, 0.5)
    assert metrics["pr_auc"] == 1.0
    assert metrics["expected_cost_per_order"] == 0.0

