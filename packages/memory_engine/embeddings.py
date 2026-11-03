from __future__ import annotations

import json

import boto3
from botocore.config import Config

EMBEDDING_DIMENSIONS = 1024


class TitanEmbedder:
    """Amazon Titan Text Embeddings V2 through Amazon Bedrock (normalized, 1024 dimensions)."""

    def __init__(self, model_id: str, region: str):
        self.model_id = model_id
        self.client = boto3.Session(region_name=region).client(
            "bedrock-runtime",
            config=Config(retries={"total_max_attempts": 3, "mode": "adaptive"}, connect_timeout=5, read_timeout=20),
        )

    def embed(self, text: str) -> list[float]:
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({"inputText": text[:8000], "dimensions": EMBEDDING_DIMENSIONS, "normalize": True}),
            contentType="application/json",
            accept="application/json",
        )
        vector = json.loads(response["body"].read())["embedding"]
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError("Unexpected embedding dimension")
        return vector
