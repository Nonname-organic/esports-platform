from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from fastapi import FastAPI
    from app.core.config import Settings


def setup_telemetry(app: "FastAPI", settings: "Settings") -> None:
    """Wire OpenTelemetry tracing into the FastAPI application.

    If OTLP_ENDPOINT is set, spans are exported via gRPC to that endpoint
    (Jaeger, ADOT Collector, etc.).  If not set, spans are created but
    discarded — zero overhead in dev without a collector running.
    """
    resource = Resource.create(
        {
            "service.name": "esports-platform-api",
            "service.version": settings.IMAGE_TAG,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI (creates spans for every HTTP request)
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    # Auto-instrument async Redis client
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument(tracer_provider=provider)
    except ImportError:
        pass

    # Auto-instrument SQLAlchemy (traces every query)
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(tracer_provider=provider)
    except ImportError:
        pass
