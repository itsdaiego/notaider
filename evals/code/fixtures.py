import shutil
import tempfile

from evals.ask.fixtures import EVAL_STORAGE, FIXTURES_DIR
from storage import Storage


def build_case_storage() -> Storage:
    """Builds a fresh, isolated Storage over its own copy of FIXTURES_DIR.

    Unlike the ask eval (read-only), @code's perform_diff really writes files
    (CodeWorkflow._apply_change), so each case needs its own disposable copy of
    sample_app rather than sharing one - otherwise cases would see each other's
    edits. The embedding model/cross-encoder are still reused from EVAL_STORAGE
    (already warmed in evals/ask/fixtures.py) rather than reloaded per case,
    since repeated SentenceTransformer re-instantiation in one process trips a
    meta-tensor bug in sentence-transformers/torch (see evals/ask/run_eval.py).
    """
    app_dir = tempfile.mkdtemp(prefix="notaider-code-eval-app-")
    shutil.copytree(FIXTURES_DIR, app_dir, dirs_exist_ok=True)

    storage_dir = tempfile.mkdtemp(prefix="notaider-code-eval-index-")
    storage = Storage(
        storage_dir=storage_dir,
        app_dir=app_dir,
        model=EVAL_STORAGE.model,
        cross_encoder=EVAL_STORAGE.cross_encoder,
    )
    storage.store_code_chunks()
    return storage
