# Hand-labeled canned answers standing in for human judgment: GOOD_ANSWERS should be
# judged as passing, BAD_ANSWERS as failing. Keyed by the same query strings used in
# evals/ask/dataset.py's CASES, so run_calibration.py can reuse each case's own
# LLMJudge rubric instead of duplicating rubric text here.

GOOD_ANSWERS: dict[str, str] = {
    "where is search_todos defined and what does it do?": (
        "search_todos is defined on the TodoManager class in todo.py. It lowercases "
        "the query and returns todos whose title or description contains it, so it's "
        "a simple case-insensitive substring search."
    ),
    "what does mark_completed do on a todo item?": (
        "mark_completed is a method on TodoItem in todo.py. It sets the item's status "
        "to TodoStatus.COMPLETED and records the current time in completed_at (and "
        "updates updated_at)."
    ),
    "which file and class contain add_todo and remove_todo?": (
        "Both add_todo and remove_todo are methods on the TodoManager class in todo.py."
    ),
    "how does the search command work in the CLI?": (
        "The search command is handled by cmd_search in cli.py. It takes the user's "
        "query argument and calls the manager's search_todos method, then prints the "
        "matching todos."
    ),
    "what search-related settings exist in the config?": (
        "In config.py, the Config class defines SEARCH_CASE_SENSITIVE, "
        "SEARCH_INCLUDE_TAGS, and SEARCH_INCLUDE_DESCRIPTION as the search-related "
        "settings."
    ),
    "where is the process_payment function implemented?": (
        "There is no process_payment function in this codebase. I searched the "
        "available files and found no payment-processing code."
    ),
}

BAD_ANSWERS: dict[str, str] = {
    "where is search_todos defined and what does it do?": (
        "search_todos is defined in cli.py inside the TodoCLI class. It prints all "
        "todos sorted by priority."
    ),
    "what does mark_completed do on a todo item?": (
        "mark_completed deletes the todo item from the manager's list and removes it "
        "from storage permanently."
    ),
    "which file and class contain add_todo and remove_todo?": (
        "add_todo and remove_todo are implemented in cli.py on the TodoCLI class."
    ),
    "how does the search command work in the CLI?": (
        "The search command in the CLI recalculates todo statistics and prints a "
        "summary of pending, completed, and cancelled todos."
    ),
    "what search-related settings exist in the config?": (
        "The config only defines database connection settings like DB_HOST and "
        "DB_PORT; there are no search-related settings."
    ),
    "where is the process_payment function implemented?": (
        "process_payment is implemented in utils.py and handles charging a user's "
        "credit card via a third-party gateway."
    ),
}
