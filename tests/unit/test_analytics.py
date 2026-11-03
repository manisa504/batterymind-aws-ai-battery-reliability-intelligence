import pandas as pd
import pytest

from packages.battery_analytics import capacity_analysis
from packages.decision_engine import Decision, classify
from packages.prediction import estimate_linear_rul


def test_capacity_analysis_honors_cutoff_and_units():
    frame = pd.DataFrame(
        {
            "battery_id": ["B1"] * 3,
            "type": ["discharge"] * 3,
            "discharge_cycle_index": [1, 2, 3],
            "capacity_ah": [2.0, 1.8, 1.6],
        }
    )
    result = capacity_analysis(frame, "B1", cutoff=2)
    assert result["latest_capacity_ah"] == pytest.approx(1.8)
    assert result["soh_percent"] == pytest.approx(90)
    assert result["cutoff_cycle"] == 2


@pytest.mark.parametrize(
    ("soh", "expected"),
    [
        (70, Decision.EOL_REVIEW),
        (70.01, Decision.ENGINEERING_REVIEW),
        (75.01, Decision.INCREASE_TESTING),
        (85.01, Decision.CONTINUE_MONITORING),
    ],
)
def test_policy_boundaries(soh, expected):
    assert classify(soh, 2).decision == expected


def test_insufficient_evidence_precedes_thresholds():
    assert classify(60, 1).decision == Decision.INSUFFICIENT_EVIDENCE


def test_rul_is_deterministic_and_separates_prediction():
    result = estimate_linear_rul([1, 2, 3, 4, 5], [2.0, 1.9, 1.8, 1.7, 1.6])
    assert result["status"] == "available"
    assert result["estimated_remaining_cycles"] == pytest.approx(2)
    assert result["prediction_kind"] == "model_prediction"
