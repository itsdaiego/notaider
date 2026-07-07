import os
import sys

from pydantic_evals import Dataset

from evals.scope.dataset import CASES
from evals.scope.evaluators import (
    ConfidenceBand,
    ScopeTypeMatch,
    TargetFileMatch,
    TargetFunctionsMatch,
    TopKSane,
)
from evals.scope.fixtures import EVAL_STATS
from scope_analyzer import ScopeAnalysis, ScopeAnalyzer

PASS_THRESHOLD = 0.85


async def run_scope_analysis(query: str) -> ScopeAnalysis:
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    analyzer = ScopeAnalyzer(model)
    return await analyzer.analyze(query, EVAL_STATS)


def main() -> int:
    dataset = Dataset(
        cases=CASES,
        evaluators=[
            ScopeTypeMatch(),
            TargetFileMatch(),
            TargetFunctionsMatch(),
            ConfidenceBand(),
            TopKSane(),
        ],
    )

    report = dataset.evaluate_sync(run_scope_analysis)
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
