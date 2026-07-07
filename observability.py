import os

from langfuse import get_client

_initialized = False


def init_observability() -> None:
    global _initialized
    if _initialized or not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return
    get_client()  # reads LANGFUSE_* env vars, registers global OTel tracer provider
    _initialized = True
