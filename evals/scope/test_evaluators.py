from typing import Any, Literal, cast

from pydantic_evals.evaluators import EvaluatorContext

from evals.scope.evaluators import (
    ConfidenceBand,
    ScopeTypeMatch,
    TargetFileMatch,
    TargetFunctionsMatch,
    TopKSane,
)
from evals.scope.fixtures import EVAL_STATS
from scope_analyzer import ScopeAnalysis

ScopeType = Literal["single", "multiple", "file", "project", "all"]


def _ctx(
    output: ScopeAnalysis, expected: ScopeAnalysis | None = None, metadata: dict | None = None
):
    return EvaluatorContext(
        name="test",
        inputs="irrelevant",
        metadata=metadata,
        expected_output=expected,
        output=output,
        duration=0.0,
        _span_tree=cast(Any, None),
        attributes={},
        metrics={},
    )


def _analysis(
    scope_type: ScopeType = "single",
    confidence: float = 0.9,
    target_file: str | None = None,
    target_functions: list[str] | None = None,
    suggested_top_k: int = 3,
) -> ScopeAnalysis:
    return ScopeAnalysis(
        scope_type=scope_type,
        confidence=confidence,
        target_file=target_file,
        target_functions=target_functions or [],
        intent_description="",
        suggested_top_k=suggested_top_k,
    )


def test_scope_type_match_pass():
    ctx = _ctx(_analysis(scope_type="file"), _analysis(scope_type="file"))
    assert ScopeTypeMatch().evaluate(ctx) is True


def test_scope_type_match_fail():
    ctx = _ctx(_analysis(scope_type="all"), _analysis(scope_type="single"))
    assert ScopeTypeMatch().evaluate(ctx) is False


def test_target_file_match_both_none():
    ctx = _ctx(_analysis(target_file=None), _analysis(target_file=None))
    assert TargetFileMatch().evaluate(ctx) is True


def test_target_file_match_fail():
    ctx = _ctx(_analysis(target_file="a.py"), _analysis(target_file="b.py"))
    assert TargetFileMatch().evaluate(ctx) is False


def test_target_functions_match_order_insensitive():
    ctx = _ctx(
        _analysis(target_functions=["b", "a"]),
        _analysis(target_functions=["a", "b"]),
    )
    assert TargetFunctionsMatch().evaluate(ctx) is True


def test_confidence_band_high_pass():
    ctx = _ctx(_analysis(confidence=0.9), metadata={"confidence_band": "high"})
    assert ConfidenceBand().evaluate(ctx) is True


def test_confidence_band_low_fail_when_too_confident():
    ctx = _ctx(_analysis(confidence=0.9), metadata={"confidence_band": "low"})
    assert ConfidenceBand().evaluate(ctx) is False


def test_confidence_band_defaults_to_high_without_metadata():
    ctx = _ctx(_analysis(confidence=0.9), metadata=None)
    assert ConfidenceBand().evaluate(ctx) is True


def test_top_k_sane_accepts_schema_max():
    # ScopeAnalysis.suggested_top_k has a hard `le=100` constraint, which is stricter than
    # EVAL_STATS.total_chunks for this fixture - so a value above total_chunks can never be
    # constructed; this just pins the boundary that IS reachable.
    ctx = _ctx(_analysis(suggested_top_k=100))
    assert TopKSane().evaluate(ctx) is True


def test_top_k_sane_file_scope_requires_exact_chunk_count():
    wrong_count = EVAL_STATS.chunks_by_file["utils.py"] - 1
    ctx = _ctx(_analysis(scope_type="file", target_file="utils.py", suggested_top_k=wrong_count))
    assert TopKSane().evaluate(ctx) is False


def test_top_k_sane_file_scope_matches_chunk_count():
    exact_count = EVAL_STATS.chunks_by_file["utils.py"]
    ctx = _ctx(_analysis(scope_type="file", target_file="utils.py", suggested_top_k=exact_count))
    assert TopKSane().evaluate(ctx) is True
