import os

from langfuse import get_client, propagate_attributes


def init_observability() -> None:
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return
    get_client()  # reads LANGFUSE_* env vars, registers global OTel tracer provider


def trace_session(session_id: str):
    """Group all spans created within the block under one Langfuse session.

    No-op when Langfuse is disabled (no LANGFUSE_PUBLIC_KEY) — safe to use unconditionally.
    """
    return propagate_attributes(session_id=session_id)
