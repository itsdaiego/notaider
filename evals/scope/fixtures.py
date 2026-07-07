import ast
from pathlib import Path

from storage import CodebaseStats

# Committed snapshot of app/ (which is gitignored and dynamically regenerated), so the eval
# is reproducible on any machine without needing a live app/ or db/ index.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_app"


def _compute_stats(source_dir: Path) -> CodebaseStats:
    """Mirrors storage.py:_parse_code_chunks's chunk-detection rule (ast.walk + FunctionDef/
    ClassDef check, AsyncFunctionDef excluded) so these stats stay faithful to what the real
    indexer would produce against the same files."""
    chunks_by_file: dict[str, int] = {}
    chunks_by_type: dict[str, int] = {"function": 0, "class": 0}

    for path in sorted(source_dir.glob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as e:
            print(f"Syntax error in {path}: {e}")
            continue

        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                chunk_type = "function" if isinstance(node, ast.FunctionDef) else "class"
                chunks_by_type[chunk_type] += 1
                count += 1

        chunks_by_file[path.name] = count

    return CodebaseStats(
        total_chunks=sum(chunks_by_file.values()),
        chunks_by_file=chunks_by_file,
        chunks_by_type=chunks_by_type,
    )


EVAL_STATS = _compute_stats(FIXTURES_DIR)
