import os
import sys
from pathlib import Path
from unittest import mock

from pydantic_evals import Dataset

from code_workflow import CodeWorkflow
from evals.code.dataset import CASES
from evals.code.fixtures import build_case_storage
from evals.code.output import CodeEvalOutput

PASS_THRESHOLD = 0.85


async def run_code(query: str) -> CodeEvalOutput:
    # Fresh isolated Storage per case: perform_diff really writes files (via
    # CodeWorkflow._apply_change), so cases must not see each other's edits.
    storage = build_case_storage()
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    workflow = CodeWorkflow(storage=storage, model=model)

    app_dir = Path(storage.app_dir)
    original_contents = {path.name: path.read_text() for path in app_dir.glob("*.py")}

    # perform_diff prompts "Apply this change? (y/n)" per change (code_workflow.py)
    # before writing to disk - always confirm, so the real end-to-end write path
    # (the thing we actually want to grade) runs exactly as it does for a real user.
    with mock.patch("builtins.input", return_value="y"):
        result_message = await workflow.perform_diff(query)

    diffs = []
    modified_files: dict[str, str] = {}
    for filename, original in original_contents.items():
        new_content = (app_dir / filename).read_text()
        if new_content != original:
            diffs.append(workflow._generate_diff(original, new_content, filename))
            modified_files[filename] = new_content

    if not diffs:
        # Low-confidence skip, "nothing found", or an error - no file was touched.
        return CodeEvalOutput(diff=f"(no changes applied) {result_message}", modified_files={})

    return CodeEvalOutput(diff="\n".join(diffs), modified_files=modified_files)


def main() -> int:
    dataset = Dataset(cases=CASES)

    # max_concurrency=1: cases share one warmed embedding model/cross-encoder
    # (see fixtures.py) - concurrent encode()/predict() calls on the same
    # instance aren't verified thread-safe (same rationale as evals/ask).
    report = dataset.evaluate_sync(run_code, max_concurrency=1)
    report.print(include_input=True, include_output=True, include_durations=True)

    total = 0
    passed = 0
    for case in report.cases:
        for result in case.assertions.values():
            total += 1
            passed += 1 if result.value else 0

    pass_rate = passed / total if total else 0.0
    print(f"\nOverall pass rate: {pass_rate:.2%} ({passed}/{total})")

    if pass_rate < PASS_THRESHOLD:
        print(f"FAILED: pass rate below threshold ({PASS_THRESHOLD:.0%})")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
