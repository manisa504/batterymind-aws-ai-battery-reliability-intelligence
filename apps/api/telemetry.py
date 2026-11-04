"""OpenTelemetry tracing for the API.

Active only when OTEL_EXPORTER_OTLP_TRACES_ENDPOINT (or OTEL_EXPORTER_OTLP_ENDPOINT) is set. On ECS the
endpoint is the CloudWatch agent sidecar (OTLP/HTTP on localhost:4318), which exports to AWS X-Ray.
Spans cover incoming FastAPI requests, SQLAlchemy queries and AWS SDK calls (Bedrock, S3).
Request bodies, prompts and model output are never recorded as span attributes.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def configure(app, engine) -> bool:
    if not enabled():
        return False
    from opentelemetry import propagate, trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.propagators.aws import AwsXRayPropagator
    from opentelemetry.sdk.extension.aws.resource.ecs import AwsEcsResourceDetector
    from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
    from opentelemetry.sdk.resources import Resource, get_aggregated_resources
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = get_aggregated_resources(
        [AwsEcsResourceDetector()],
        initial_resource=Resource.create({"service.name": os.environ.get("OTEL_SERVICE_NAME", "batterymind-api")}),
    )
    # X-Ray-compatible trace IDs keep traces queryable in X-Ray and CloudWatch.
    provider = TracerProvider(resource=resource, id_generator=AwsXRayIdGenerator())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    propagate.set_global_textmap(AwsXRayPropagator())
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health", tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)
    BotocoreInstrumentor().instrument(tracer_provider=provider)
    log.info("OpenTelemetry tracing enabled")
    return True
