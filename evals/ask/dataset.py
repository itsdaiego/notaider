from typing import Final

from pydantic_ai.settings import ModelSettings
from pydantic_evals import Case
from pydantic_evals.evaluators import LLMJudge

JUDGE_MODEL: Final = "openai:gpt-4o"
JUDGE_MODEL_SETTINGS: Final[ModelSettings] = {"temperature": 0}

CASES = [
    # -- locate a function --
    Case(
        name="locate-search-todos",
        inputs="where is search_todos defined and what does it do?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must state that search_todos is defined in todo.py "
                    "(on the TodoManager class) and that it searches todos by matching "
                    "the query against the title or description, case-insensitively. "
                    "It must not attribute the function to a different file."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
    # -- explain behavior of a method --
    Case(
        name="explain-mark-completed",
        inputs="what does mark_completed do on a todo item?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must explain that mark_completed (on TodoItem in todo.py) "
                    "sets the item's status to completed and records a completed_at "
                    "timestamp. It should not describe unrelated behavior like deleting "
                    "or removing the todo."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
    # -- which file / class --
    Case(
        name="which-file-add-remove-todo",
        inputs="which file and class contain add_todo and remove_todo?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must name todo.py and the TodoManager class as where "
                    "both add_todo and remove_todo live. It must not claim they live in "
                    "cli.py or a different class."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
    # -- explain a CLI command handler --
    Case(
        name="explain-cmd-search",
        inputs="how does the search command work in the CLI?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must reference cmd_search in cli.py and explain that it "
                    "calls the manager's search_todos method with the user's query and "
                    "prints the matching results."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
    # -- config lookup --
    Case(
        name="config-search-settings",
        inputs="what search-related settings exist in the config?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must mention config.py and at least two of: "
                    "SEARCH_CASE_SENSITIVE, SEARCH_INCLUDE_TAGS, SEARCH_INCLUDE_DESCRIPTION."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
    # -- not in the codebase: must not hallucinate --
    Case(
        name="not-found-payment",
        inputs="where is the process_payment function implemented?",
        evaluators=(
            LLMJudge(
                rubric=(
                    "The answer must state that no such function (process_payment, or "
                    "any payment-processing code) exists in this codebase, rather than "
                    "inventing a file or function name for it."
                ),
                model=JUDGE_MODEL,
                model_settings=JUDGE_MODEL_SETTINGS,
            ),
        ),
    ),
]
