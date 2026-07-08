import sys

from pydantic_evals import Dataset

from evals.ask.calibration import BAD_ANSWERS, GOOD_ANSWERS
from evals.ask.dataset import CASES

AGREEMENT_THRESHOLD = 0.85


async def run_good(query: str) -> str:
    return GOOD_ANSWERS[query]


async def run_bad(query: str) -> str:
    return BAD_ANSWERS[query]


def main() -> int:
    dataset = Dataset(cases=CASES)

    good_report = dataset.evaluate_sync(run_good, name="calibration-good")
    bad_report = dataset.evaluate_sync(run_bad, name="calibration-bad")

    total = 0
    agreed = 0

    print("\n-- good answers (expect judge: pass) --")
    for case in good_report.cases:
        for result in case.assertions.values():
            total += 1
            matched = bool(result.value)
            agreed += 1 if matched else 0
            verdict = "pass" if result.value else "FAIL"
            print(f"  {case.name}: judge={verdict} {'OK' if matched else 'MISMATCH'}")

    print("\n-- bad answers (expect judge: fail) --")
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
