"""Thin, bounded wrapper around the Amazon Bedrock Converse API."""

from __future__ import annotations

import time
from functools import lru_cache

import boto3
from botocore.config import Config

from .settings import settings


@lru_cache
def _client():
    return boto3.Session(region_name=settings.aws_region).client(
        "bedrock-runtime",
        config=Config(retries={"total_max_attempts": 3, "mode": "adaptive"}, connect_timeout=5, read_timeout=30),
    )


def converse(system: str, messages: list[dict], max_tokens: int | None = None) -> dict:
    """Return {text, model_id, input_tokens, output_tokens, latency_ms}. Raises on Bedrock failure."""
    if not settings.bedrock_model_id:
        raise RuntimeError("Bedrock model is not configured")
    started = time.perf_counter()
    reply = _client().converse(
        modelId=settings.bedrock_model_id,
        system=[{"text": system}],
        messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
        inferenceConfig={"maxTokens": max_tokens or settings.bedrock_max_tokens, "temperature": 0.1},
    )
    text = "".join(b.get("text", "") for b in reply["output"]["message"]["content"]).strip()
    usage = reply.get("usage", {})
    return {
        "text": text,
        "model_id": settings.bedrock_model_id,
        "input_tokens": int(usage.get("inputTokens", 0)),
        "output_tokens": int(usage.get("outputTokens", 0)),
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
