import ast
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.code.output import CodeEvalOutput


@dataclass
class SyntaxValid(Evaluator[str, CodeEvalOutput, dict]):
    """Deterministic gate: the resulting file(s) must still be valid Python.

    Orthogonal to LLMJudge's semantic plausibility check - a diff can be
    semantically wrong yet still parse fine, and (more importantly) a diff can
    be well-intentioned yet break indentation/syntax. No LLM call needed since
    ast.parse either succeeds or it doesn't.
    """

    def evaluate(self, ctx: EvaluatorContext[str, CodeEvalOutput, dict]) -> bool:
        for content in ctx.output.modified_files.values():
            try:
                ast.parse(content)
            except SyntaxError:
                return False
        return True
