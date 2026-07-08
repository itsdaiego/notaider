import tempfile
from pathlib import Path

from storage import Storage

# Same committed snapshot the scope evals use (see evals/scope/fixtures.py) — a
# small fake "todo" app that stands in for a real indexed codebase.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_app"


def _build_storage() -> Storage:
    """Builds a real FAISS chunk index over FIXTURES_DIR in a throwaway directory,
    so the ask eval exercises the actual retrieval/reranking pipeline end-to-end."""
    storage_dir = tempfile.mkdtemp(prefix="notaider-ask-eval-")
    storage = Storage(storage_dir=storage_dir, app_dir=str(FIXTURES_DIR))
    storage.store_code_chunks()
    return storage


# Built once per process and reused across every case in the dataset.
EVAL_STORAGE = _build_storage()
