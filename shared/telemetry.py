from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
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


class OpenTelemetryCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that creates OpenTelemetry spans for LLM calls."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._spans: dict[UUID, trace.Span] = {}

    def _serialize_messages(self, messages: list[list[BaseMessage]]) -> str:
        """Convert messages to a readable string format."""

        lines = []
        for batch in messages:
            for msg in batch:
                role = msg.type if hasattr(msg, "type") else "unknown"
                content = msg.content if hasattr(msg, "content") else str(msg)
                lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Create a span when a chat model call starts."""

        tracer = get_tracer()
        model_name = kwargs.get("invocation_params", {}).get("model", "unknown")

        span = tracer.start_span(f"llm.{self.agent_name}")
        span.set_attribute("llm.model", model_name)
        span.set_attribute("llm.agent", self.agent_name)
        span.set_attribute("llm.message_count", sum(len(batch) for batch in messages))
        span.set_attribute("llm.prompt", self._serialize_messages(messages))

        self._spans[run_id] = span

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        """End the span when LLM call completes."""

        if span := self._spans.pop(run_id, None):
            if response.llm_output:
                if usage := response.llm_output.get("usage", {}):
                    span.set_attribute("llm.input_tokens", usage.get("input_tokens", 0))
                    span.set_attribute("llm.output_tokens", usage.get("output_tokens", 0))

            if response.generations and response.generations[0]:
                generation = response.generations[0][0]
                if hasattr(generation, "text"):
                    span.set_attribute("llm.response", generation.text)
                elif hasattr(generation, "message") and hasattr(generation.message, "content"):
                    span.set_attribute("llm.response", generation.message.content)

            span.end()

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Record error and end span if LLM call fails."""

        if span := self._spans.pop(run_id, None):
            span.set_attribute("error", True)
            span.record_exception(error)
            span.end()
