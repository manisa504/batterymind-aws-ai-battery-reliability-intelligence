from __future__ import annotations

import boto3
from botocore.config import Config


class BedrockExplainer:
    def __init__(self, model_id: str, region: str = "us-east-2", max_tokens: int = 500):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.client = boto3.Session(region_name=region).client(
            "bedrock-runtime",
            config=Config(retries={"total_max_attempts": 5, "mode": "adaptive"}, connect_timeout=5, read_timeout=30),
        )

    def explain(self, structured_evidence: dict, historical_context: list[str]) -> tuple[str, dict]:
        prompt = (
            "Explain this deterministic battery assessment using only the supplied evidence. "
            "Distinguish measurements from predictions and avoid field-safety claims.\n"
            f"Evidence: {structured_evidence}\nPrior valid assessments: {historical_context[:5]}"
        )
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0.1},
            requestMetadata={"application": "BatteryMind"},
        )
        text = "".join(block.get("text", "") for block in response["output"]["message"]["content"])
        return text, response.get("usage", {})
