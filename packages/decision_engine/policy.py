from dataclasses import dataclass
from enum import StrEnum

POLICY_VERSION = "experimental-soh-v1"


class Decision(StrEnum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    INCREASE_TESTING = "INCREASE_TESTING"
    ENGINEERING_REVIEW = "ENGINEERING_REVIEW"
    EOL_REVIEW = "EOL_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class Classification:
    decision: Decision
    policy_version: str
    rationale: str


def classify(soh_percent: float | None, valid_measurements: int) -> Classification:
    if soh_percent is None or valid_measurements < 2:
        return Classification(
            Decision.INSUFFICIENT_EVIDENCE, POLICY_VERSION, "At least two valid capacity measurements are required."
        )
    if soh_percent <= 70:
        decision = Decision.EOL_REVIEW
    elif soh_percent <= 75:
        decision = Decision.ENGINEERING_REVIEW
    elif soh_percent <= 85:
        decision = Decision.INCREASE_TESTING
    else:
        decision = Decision.CONTINUE_MONITORING
    return Classification(
        decision,
        POLICY_VERSION,
        "Classification uses project-defined SOH bands; only the 70% threshold corresponds "
        "to this NASA experiment's 2 Ah to 1.4 Ah criterion.",
    )
