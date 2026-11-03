"""LLM explanation of an already-computed assessment.

The model only rephrases measured and derived values supplied in the prompt; it never produces
them. If Bedrock is unconfigured or fails, the deterministic rule-based rationale is used.
"""

import logging

import boto3

from .settings import settings

log = logging.getLogger(__name__)

_PROMPT = (
    "You are explaining a laboratory battery-aging assessment to an engineer. Use only the numbers "
    "below; do not invent values or thresholds, and make no numeric comparison other than stating the "
    "decision band given. State that this is a NASA laboratory experiment, not field data. "
    "Write at most 3 sentences.\n"
    "Battery: {battery_id}\nCutoff cycle: {cutoff}\nMeasured latest capacity (Ah): {cap:.3f}\n"
    "Derived state of health (%): {soh:.1f}\nDecision: {decision}\n"
    "Decision bands by SOH: <=70 EOL_REVIEW; >70 to 75 ENGINEERING_REVIEW; >75 to 85 INCREASE_TESTING; "
    ">85 CONTINUE_MONITORING. Only the 70% line matches the NASA end-of-life criterion; the others are "
    "project-defined.\nRule-based rationale: {rationale}"
)


def explain(analysis: dict) -> tuple[str, str | None]:
    """Return (explanation, model_id). model_id is None when the rule-based text was used."""
    rationale = analysis["classification"]["rationale"]
    if not settings.bedrock_model_id:
        return rationale, None
    prompt = _PROMPT.format(
        battery_id=analysis["battery_id"],
        cutoff=analysis["cutoff_cycle"],
        cap=analysis["latest_capacity_ah"],
        soh=analysis["soh_percent"],
        decision=analysis["classification"]["decision"],
        rationale=rationale,
    )
    try:
        client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        reply = client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": settings.bedrock_max_tokens, "temperature": 0.2},
        )
        text = reply["output"]["message"]["content"][0]["text"].strip()
        return (text or rationale), (settings.bedrock_model_id if text else None)
    except Exception:  # noqa: BLE001 - any Bedrock failure must degrade to the deterministic text
        log.exception("Bedrock explanation failed; using rule-based rationale")
        return rationale, None
