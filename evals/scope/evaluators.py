from dataclasses import dataclass
from typing import Literal

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.scope.fixtures import EVAL_STATS
from scope_analyzer import ScopeAnalysis


@dataclass
class ConfidenceBand(Evaluator[str, ScopeAnalysis, dict]):
    """Checks output confidence falls in the specified band."""

    band: Literal["high", "medium", "low"] = "high"

    def evaluate(self, ctx: EvaluatorContext[str, ScopeAnalysis, dict]) -> bool:
        confidence = ctx.output.confidence
        if self.band == "high":
            return confidence >= 0.8
        if self.band == "medium":
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
