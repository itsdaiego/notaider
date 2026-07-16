from typing import Literal

from pydantic_evals import Case

from evals.scope.evaluators import ConfidenceBand
from scope_analyzer import ScopeAnalysis

ScopeType = Literal["single", "multiple", "file", "project", "all"]


def expected(
    scope_type: ScopeType,
    target_file: str | None = None,
    target_functions: list[str] | None = None,
) -> ScopeAnalysis:
    return ScopeAnalysis(
        scope_type=scope_type,
        confidence=0.0,
        target_file=target_file,
        target_functions=target_functions or [],
        intent_description="",
        suggested_top_k=1,
    )


CASES = [
    # -- single: one specific function/class --
    Case(
        name="single-add-print",
        inputs="add print statement to get_todo",
        expected_output=expected("single", target_functions=["get_todo"]),
    ),
    Case(
        name="single-add-logging",
        inputs="add logging to add_tag",
        expected_output=expected("single", target_functions=["add_tag"]),
    ),
    Case(
        name="single-raise-exception",
        inputs="update mark_completed to raise an exception if already completed",
        expected_output=expected("single", target_functions=["mark_completed"]),
    ),
    Case(
        name="single-sanitize-tag",
        inputs="add validation to sanitize_tag",
        expected_output=expected("single", target_functions=["sanitize_tag"]),
    ),
    # -- multiple: several specific named items --
    Case(
        name="multiple-add-remove-todo",
        inputs="update add_todo and remove_todo to log their calls",
        expected_output=expected("multiple", target_functions=["add_todo", "remove_todo"]),
    ),
    Case(
        name="multiple-validation-funcs",
        inputs="refactor validate_title and validate_description to trim whitespace",
        expected_output=expected(
            "multiple", target_functions=["validate_title", "validate_description"]
        ),
    ),
    Case(
        name="multiple-parse-funcs",
        inputs="update parse_priority and parse_status to handle invalid input",
        expected_output=expected("multiple", target_functions=["parse_priority", "parse_status"]),
    ),
    # -- file: all matching items in one named file --
    Case(
        name="file-utils-docstrings",
        inputs="add docstrings to every function in utils.py",
        expected_output=expected("file", target_file="utils.py"),
    ),
    Case(
        name="file-todo-type-hints",
        inputs="add type hints to all functions in todo.py",
        expected_output=expected("file", target_file="todo.py"),
    ),
    Case(
        name="file-config-comments",
        inputs="update all methods in config.py to include comments",
        expected_output=expected("file", target_file="config.py"),
    ),
    Case(
        name="file-sample-data-comments",
        inputs="add comments to all methods in sample_data.py",
        expected_output=expected("file", target_file="sample_data.py"),
    ),
    # -- project / all: broad, no single file named --
    Case(
        name="project-type-hints-everywhere",
        inputs="add type hints to all functions",
        expected_output=expected("project"),
    ),
    Case(
        name="all-refactor-error-handling",
        inputs="refactor all error handling across the codebase",
        expected_output=expected("all"),
    ),
    # -- vague queries: must yield low confidence, guarding the code_workflow.py:202 gate --
    Case(
        name="vague-fix-it",
        inputs="fix it",
        expected_output=expected("single"),
        evaluators=(ConfidenceBand("low"),),
    ),
    Case(
        name="vague-make-better",
        inputs="make it better",
        expected_output=expected("single"),
        evaluators=(ConfidenceBand("low"),),
    ),
    Case(
        name="vague-improve-code",
        inputs="improve the code",
        expected_output=expected("single"),
        evaluators=(ConfidenceBand("low"),),
    ),
    Case(
        name="vague-handle-properly",
        inputs="handle this properly",
        expected_output=expected("single"),
        evaluators=(ConfidenceBand("low"),),
    ),
]
