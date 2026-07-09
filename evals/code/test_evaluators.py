from typing import Any, cast

from pydantic_evals.evaluators import EvaluatorContext

from evals.code.evaluators import SyntaxValid
from evals.code.output import CodeEvalOutput


def _ctx(output: CodeEvalOutput) -> EvaluatorContext[str, CodeEvalOutput, dict]:
    return EvaluatorContext(
        name="test",
        inputs="irrelevant",
        metadata=None,
        expected_output=None,
        output=output,
        duration=0.0,
        _span_tree=cast(Any, None),
        attributes={},
        metrics={},
    )


def test_syntax_valid_passes_valid_python():
    output = CodeEvalOutput(diff="", modified_files={"a.py": "def foo():\n    return 1\n"})
    assert SyntaxValid().evaluate(_ctx(output)) is True


def test_syntax_valid_fails_broken_python():
    output = CodeEvalOutput(diff="", modified_files={"a.py": "def foo(:\n    return 1\n"})
    assert SyntaxValid().evaluate(_ctx(output)) is False


def test_syntax_valid_fails_bad_indentation():
    output = CodeEvalOutput(
        diff="", modified_files={"a.py": "def foo():\n    return 1\n  bad_indent = True\n"}
    )
    assert SyntaxValid().evaluate(_ctx(output)) is False


def test_syntax_valid_checks_every_file():
    output = CodeEvalOutput(
        diff="",
        modified_files={
            "a.py": "def foo():\n    return 1\n",
            "b.py": "def bar(:\n    return 2\n",
        },
    )
    assert SyntaxValid().evaluate(_ctx(output)) is False


def test_syntax_valid_passes_no_files_changed():
    # No changes were applied (e.g. low-confidence/not-found guard) - nothing to check.
    output = CodeEvalOutput(diff="(no changes applied) Nothing found.", modified_files={})
    assert SyntaxValid().evaluate(_ctx(output)) is True
