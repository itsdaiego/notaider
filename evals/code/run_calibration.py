import sys

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from evals.ask.dataset import JUDGE_MODEL, JUDGE_MODEL_SETTINGS
from evals.code.calibration import BAD_OUTPUTS, GOOD_OUTPUTS
from evals.code.dataset import CASE_DEFINITIONS
from evals.code.output import CodeEvalOutput

AGREEMENT_THRESHOLD = 0.85


def _judge_only_cases() -> list[Case]:
    return [
        Case(
            name=name,
            inputs=query,
            evaluators=(
                LLMJudge(rubric=rubric, model=JUDGE_MODEL, model_settings=JUDGE_MODEL_SETTINGS),
            ),
        )
        for name, query, rubric in CASE_DEFINITIONS
    ]


async def run_good(query: str) -> CodeEvalOutput:
    return GOOD_OUTPUTS[query]


async def run_bad(query: str) -> CodeEvalOutput:
    return BAD_OUTPUTS[query]


def main() -> int:
    dataset = Dataset(cases=_judge_only_cases())

    good_report = dataset.evaluate_sync(run_good, name="calibration-good")
    bad_report = dataset.evaluate_sync(run_bad, name="calibration-bad")

    total = 0
    agreed = 0

    print("\n-- good outputs (expect judge: pass) --")
    for case in good_report.cases:
        for result in case.assertions.values():
            total += 1
            matched = bool(result.value)
            agreed += 1 if matched else 0
            verdict = "pass" if result.value else "FAIL"
            print(f"  {case.name}: judge={verdict} {'OK' if matched else 'MISMATCH'}")

    print("\n-- bad outputs (expect judge: fail) --")
    for case in bad_report.cases:
        for result in case.assertions.values():
            total += 1
            matched = not bool(result.value)
            agreed += 1 if matched else 0
            verdict = "pass" if result.value else "FAIL"
            print(f"  {case.name}: judge={verdict} {'OK' if matched else 'MISMATCH'}")

    agreement_rate = agreed / total if total else 0.0
    print(f"\nJudge/label agreement: {agreement_rate:.2%} ({agreed}/{total})")

    if agreement_rate < AGREEMENT_THRESHOLD:
        print(f"FAILED: agreement below threshold ({AGREEMENT_THRESHOLD:.0%})")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
