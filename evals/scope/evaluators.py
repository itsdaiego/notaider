from dataclasses import dataclass
from typing import Literal

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.scope.fixtures import EVAL_STATS
from scope_analyzer import ScopeAnalysis


@dataclass
class ScopeTypeMatch(Evaluator[str, ScopeAnalysis, dict]):
    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        if ctx.expected_output is None:
            return True
        return ctx.output.scope_type == ctx.expected_output.scope_type


@dataclass
class TargetFileMatch(Evaluator[str, ScopeAnalysis, dict]):
    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        if ctx.expected_output is None:
            return True
        return ctx.output.target_file == ctx.expected_output.target_file


@dataclass
class TargetFunctionsMatch(Evaluator[str, ScopeAnalysis, dict]):
    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        if ctx.expected_output is None:
            return True
        return set(ctx.output.target_functions) == set(ctx.expected_output.target_functions)


@dataclass
class ConfidenceBand(Evaluator[str, ScopeAnalysis, dict]):
    """Checks confidence falls in the band implied by the case's metadata, not an exact value."""

    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        band: Literal["high", "medium", "low"] = (ctx.metadata or {}).get("confidence_band", "high")
        confidence = ctx.output.confidence
        if band == "high":
            return confidence >= 0.8
        if band == "medium":
            return 0.5 <= confidence < 0.8
        return confidence < 0.5


@dataclass
class TopKSane(Evaluator[str, ScopeAnalysis, dict]):
    """Mirrors the prompt's own contract: top_k in range, and exact for file scope."""

    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        top_k = ctx.output.suggested_top_k
        if not (1 <= top_k <= EVAL_STATS.total_chunks):
            return False

        if ctx.output.scope_type == "file" and ctx.output.target_file:
            expected_count = EVAL_STATS.chunks_by_file.get(ctx.output.target_file)
            if expected_count is not None:
                return top_k == expected_count

        return True
