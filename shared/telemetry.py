from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from shared.config import get_settings


def init_telemetry(jaeger_endpoint: str | None = None) -> trace.Tracer:

    # Section 1: Import configuration settings
    settings = get_settings()
    endpoint = jaeger_endpoint or settings.telemetry.jaeger_endpoint
    service_name = settings.telemetry.service_name

    # Section 2: Configure the tracer provider with the service name resource
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Section 3: Configure OTLP exporter to send traces to Jaeger
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    print(f"Telemetry initialized - view traces at {settings.telemetry.jaeger_ui_url}")
    return trace.get_tracer(service_name)


def get_tracer() -> trace.Tracer:
    """Get the tracer instance. Call init_telemetry() first."""

    settings = get_settings()
    return trace.get_tracer(settings.telemetry.service_name)
