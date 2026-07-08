import os
import sys

from pydantic_evals import Dataset
from pydantic_evals.evaluators import LLMJudge

from evals.ask.dataset import CASES, JUDGE_MODEL, JUDGE_MODEL_SETTINGS
from evals.ask.fixtures import EVAL_STORAGE
from main import NotAider

PASS_THRESHOLD = 0.85

GENERAL_RUBRIC = (
    "The answer is concrete and grounded in the retrieved code: it references real "
    "function, class, or file names rather than vague hand-waving or generic advice."
)


async def run_ask(query: str) -> str:
    # Reuse EVAL_STORAGE (built once in fixtures.py) across every case instead of
    # letting each NotAider() build its own Storage: SentenceTransformer/CrossEncoder
    # are lazily loaded on first use, and repeated re-instantiation of the same model
    # in one process trips a meta-tensor bug in sentence-transformers/torch.
    api_key = os.getenv("OPENAI_API_KEY") or ""
    notaider = NotAider(api_key, storage=EVAL_STORAGE)
    return await notaider.enhance_prompt(query)


def main() -> int:
    dataset = Dataset(
        cases=CASES,
        evaluators=[
            LLMJudge(
                rubric=GENERAL_RUBRIC,
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            )
        ],
    )

    # max_concurrency=1: all cases share one Storage instance (see run_ask), and
    # SentenceTransformer/CrossEncoder aren't verified thread-safe for concurrent
    # encode()/predict() calls on the same instance.
    report = dataset.evaluate_sync(run_ask, max_concurrency=1)
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
