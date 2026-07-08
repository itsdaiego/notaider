import os

from langfuse import get_client


def init_observability() -> None:
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return
    get_client()  # reads LANGFUSE_* env vars, registers global OTel tracer provider
