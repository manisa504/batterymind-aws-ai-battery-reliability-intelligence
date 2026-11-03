"""LLM explanation of an already-computed assessment.

The model only rephrases measured and derived values supplied in the prompt; it never produces
them. If Bedrock is unconfigured or fails, the deterministic rule-based rationale is used.
"""

import logging

from . import llm
from .settings import settings

log = logging.getLogger(__name__)

SYSTEM = (
    "You explain a laboratory battery-aging assessment to an engineer. Use only the numbers provided; "
    "do not invent values or thresholds, and make no numeric comparison other than stating the decision "
    "band given. State that this is a NASA laboratory experiment, not field data. Write at most 3 sentences."
)

DECISION_BANDS = (
    "Decision bands by SOH: <=70 EOL_REVIEW; >70 to 75 ENGINEERING_REVIEW; >75 to 85 INCREASE_TESTING; "
    ">85 CONTINUE_MONITORING. Only the 70% line matches the NASA end-of-life criterion; the others are "
    "project-defined."
)


def explain(analysis: dict) -> tuple[str, str | None]:
    """Return (explanation, model_id). model_id is None when the rule-based text was used."""
    rationale = analysis["classification"]["rationale"]
    if not settings.bedrock_model_id:
        return rationale, None
    prompt = (
        f"Battery: {analysis['battery_id']}\nCutoff cycle: {analysis['cutoff_cycle']}\n"
        f"Measured latest capacity (Ah): {analysis['latest_capacity_ah']:.3f}\n"
        f"Derived state of health (%): {analysis['soh_percent']:.1f}\n"
        f"Decision: {analysis['classification']['decision']}\n{DECISION_BANDS}\n"
        f"Rule-based rationale: {rationale}"
    )
    try:
        reply = llm.converse(SYSTEM, [{"role": "user", "content": prompt}])
        return (reply["text"] or rationale), (reply["model_id"] if reply["text"] else None)
    except Exception:  # noqa: BLE001 - any Bedrock failure must degrade to the deterministic text
        log.exception("Bedrock explanation failed; using rule-based rationale")
        return rationale, None
