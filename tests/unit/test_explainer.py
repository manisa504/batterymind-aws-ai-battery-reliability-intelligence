from apps.api import explainer

ANALYSIS = {
    "battery_id": "B0005",
    "cutoff_cycle": 120,
    "latest_capacity_ah": 1.433,
    "soh_percent": 71.7,
    "classification": {"decision": "ENGINEERING_REVIEW", "rationale": "rule text"},
}


def test_rule_based_when_bedrock_unconfigured(monkeypatch):
    monkeypatch.setattr(explainer.settings, "bedrock_model_id", None)
    assert explainer.explain(ANALYSIS) == ("rule text", None)


def test_falls_back_when_bedrock_fails(monkeypatch):
    monkeypatch.setattr(explainer.settings, "bedrock_model_id", "m")

    def boom(*a, **k):
        raise RuntimeError("no bedrock")

    monkeypatch.setattr(explainer.boto3, "client", boom)
    assert explainer.explain(ANALYSIS) == ("rule text", None)
