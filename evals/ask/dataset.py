from typing import Final

from pydantic_ai.settings import ModelSettings
from pydantic_evals import Case
from pydantic_evals.evaluators import LLMJudge

JUDGE_MODEL: Final = "openai:gpt-4o"
JUDGE_MODEL_SETTINGS: Final[ModelSettings] = {"temperature": 0}

Q_LOCATE_SEARCH_TODOS = "where is search_todos defined and what does it do?"
Q_EXPLAIN_MARK_COMPLETED = "what does mark_completed do on a todo item?"
Q_WHICH_FILE_ADD_REMOVE = "which file and class contain add_todo and remove_todo?"
Q_EXPLAIN_CMD_SEARCH = "how does the search command work in the CLI?"
Q_CONFIG_SEARCH_SETTINGS = "what search-related settings exist in the config?"
Q_NOT_FOUND_PAYMENT = "where is the process_payment function implemented?"

CASES = [
    Case(
        name="locate-search-todos",
        inputs=Q_LOCATE_SEARCH_TODOS,
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
    Case(
        name="explain-mark-completed",
        inputs=Q_EXPLAIN_MARK_COMPLETED,
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
    Case(
        name="which-file-add-remove-todo",
        inputs=Q_WHICH_FILE_ADD_REMOVE,
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
    Case(
        name="explain-cmd-search",
        inputs=Q_EXPLAIN_CMD_SEARCH,
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
    Case(
        name="config-search-settings",
        inputs=Q_CONFIG_SEARCH_SETTINGS,
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
    Case(
        name="not-found-payment",
        inputs=Q_NOT_FOUND_PAYMENT,
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
