import ast
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.code.output import CodeEvalOutput


@dataclass
class SyntaxValid(Evaluator[str, CodeEvalOutput, dict]):
    def evaluate(self, ctx: EvaluatorContext[str, CodeEvalOutput, dict]) -> bool:
        for content in ctx.output.modified_files.values():
            try:
                ast.parse(content)
            except SyntaxError:
                return False
        return True
