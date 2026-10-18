from dataclasses import replace
import math

import pytest

from utils.acceptance_gate import assess_metrics
from utils.config import AcceptancePolicy


BASELINE = {"f1_score": 0.6040462428, "recall": 0.5588235294,
            "precision": 0.6572327044, "roc_auc": 0.8418378155}


def test_corrected_baseline_meets_initial_retention_policy():
    assert all(check["passed"] for check in assess_metrics(BASELINE, AcceptancePolicy(), BASELINE))


@pytest.mark.parametrize("metric,value", [("f1_score", 0.59), ("recall", 0.54),
                                         ("precision", 0.62), ("roc_auc", 0.82),
                                         ("f1_score", math.nan), ("recall", math.inf)])
def test_each_quality_floor_rejects_a_regression(metric, value):
    assert not all(check["passed"] for check in assess_metrics({**BASELINE, metric: value}, AcceptancePolicy()))


def test_retention_recall_cannot_regress_beyond_tolerance_even_above_floor():
    improved_reference = {**BASELINE, "recall": 0.7}
    assert not all(check["passed"] for check in assess_metrics(BASELINE, AcceptancePolicy(), improved_reference))


def test_policy_rejects_nonfinite_or_invalid_limits():
    with pytest.raises(ValueError):
        replace(AcceptancePolicy(), min_f1=math.nan)
    with pytest.raises(ValueError):
        replace(AcceptancePolicy(), max_recall_drop=-0.01)
