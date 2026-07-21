from evals.ask.dataset import (
    Q_CONFIG_SEARCH_SETTINGS,
    Q_EXPLAIN_CMD_SEARCH,
    Q_EXPLAIN_MARK_COMPLETED,
    Q_LOCATE_SEARCH_TODOS,
    Q_NOT_FOUND_PAYMENT,
    Q_WHICH_FILE_ADD_REMOVE,
)

GOOD_ANSWERS: dict[str, str] = {
    Q_LOCATE_SEARCH_TODOS: (
        "search_todos is defined on the TodoManager class in todo.py. It lowercases "
        "the query and returns todos whose title or description contains it, so it's "
        "a simple case-insensitive substring search."
    ),
    Q_EXPLAIN_MARK_COMPLETED: (
        "mark_completed is a method on TodoItem in todo.py. It sets the item's status "
        "to TodoStatus.COMPLETED and records the current time in completed_at (and "
        "updates updated_at)."
    ),
    Q_WHICH_FILE_ADD_REMOVE: (
        "Both add_todo and remove_todo are methods on the TodoManager class in todo.py."
    ),
    Q_EXPLAIN_CMD_SEARCH: (
        "The search command is handled by cmd_search in cli.py. It takes the user's "
        "query argument and calls the manager's search_todos method, then prints the "
        "matching todos."
    ),
    Q_CONFIG_SEARCH_SETTINGS: (
        "In config.py, the Config class defines SEARCH_CASE_SENSITIVE, "
        "SEARCH_INCLUDE_TAGS, and SEARCH_INCLUDE_DESCRIPTION as the search-related "
        "settings."
    ),
    Q_NOT_FOUND_PAYMENT: (
        "There is no process_payment function in this codebase. I searched the "
        "available files and found no payment-processing code."
    ),
}

BAD_ANSWERS: dict[str, str] = {
    "where is search_todos defined and what does it do?": (
        "search_todos is defined in cli.py inside the TodoCLI class. It prints all "
        "todos sorted by priority."
    ),
    Q_EXPLAIN_MARK_COMPLETED: (
        "mark_completed deletes the todo item from the manager's list and removes it "
        "from storage permanently."
    ),
    Q_WHICH_FILE_ADD_REMOVE: (
        "add_todo and remove_todo are implemented in cli.py on the TodoCLI class."
    ),
    Q_EXPLAIN_CMD_SEARCH: (
        "The search command in the CLI recalculates todo statistics and prints a "
        "summary of pending, completed, and cancelled todos."
    ),
    Q_CONFIG_SEARCH_SETTINGS: (
        "The config only defines database connection settings like DB_HOST and "
        "DB_PORT; there are no search-related settings."
    ),
    Q_NOT_FOUND_PAYMENT: (
        "process_payment is implemented in utils.py and handles charging a user's "
        "credit card via a third-party gateway."
    ),
}
