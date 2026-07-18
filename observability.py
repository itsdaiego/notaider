import os
from contextlib import contextmanager

from langfuse import get_client, propagate_attributes
from opentelemetry import trace


def init_observability() -> None:
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return
    get_client()


@contextmanager
def trace_session(session_id: str, tags: list[str] | None = None, name: str = "trace"):
    """Create a root span and group all nested spans under one Langfuse session."""
    tracer = trace.get_tracer(__name__)
    with propagate_attributes(session_id=session_id, tags=tags or []):
        with tracer.start_as_current_span(name):
            yield
