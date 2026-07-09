from evals.code.output import CodeEvalOutput

# Hand-labeled canned CodeEvalOutputs standing in for human judgment: GOOD_OUTPUTS
# should be judged as passing, BAD_OUTPUTS as failing. Keyed by the same query
# strings as evals/code/dataset.py's CASE_DEFINITIONS, so run_calibration.py can
# reuse each query's own name/rubric instead of duplicating them here.
# modified_files snippets are illustrative, not full files - calibration only runs
# LLMJudge (not SyntaxValid, see run_calibration.py), so they don't need to be
# complete/parseable file contents.

GOOD_OUTPUTS: dict[str, CodeEvalOutput] = {
    "add a print statement logging the query at the start of search_todos": CodeEvalOutput(
        diff=(
            "--- a/todo.py\n+++ b/todo.py\n@@ -197,6 +197,7 @@\n"
            "     def search_todos(self, query: str) -> List[TodoItem]:\n"
            '         """Search todos by title or description"""\n'
            '+        print(f"Searching todos with query: {query}")\n'
            "         query = query.lower()\n"
        ),
        modified_files={
            "todo.py": (
                "    def search_todos(self, query: str) -> List[TodoItem]:\n"
                '        """Search todos by title or description"""\n'
                '        print(f"Searching todos with query: {query}")\n'
                "        query = query.lower()\n"
                "        return [todo for todo in self.todos\n"
                "                if query in todo.title.lower()\n"
                "                or query in todo.description.lower()]\n"
            )
        },
    ),
    "add validation to search_todos in todo.py to ignore empty or blank queries, "
    "and add a docstring to cmd_search in cli.py explaining what it does": CodeEvalOutput(
        diff=(
            "--- a/todo.py\n+++ b/todo.py\n@@ -197,6 +197,8 @@\n"
            "     def search_todos(self, query: str) -> List[TodoItem]:\n"
            '         """Search todos by title or description"""\n'
            "+        if not query or not query.strip():\n"
            "+            return []\n"
            "         query = query.lower()\n"
            "\n"
            "--- a/cli.py\n+++ b/cli.py\n@@ -289,7 +289,7 @@\n"
            "     def cmd_search(self, args):\n"
            '-        """Search for todos"""\n'
            '+        """Search todos matching the given query and print the results."""\n'
            "         todos = self.manager.search_todos(args.query)\n"
        ),
        modified_files={
            "todo.py": (
                "    def search_todos(self, query: str) -> List[TodoItem]:\n"
                '        """Search todos by title or description"""\n'
                "        if not query or not query.strip():\n"
                "            return []\n"
                "        query = query.lower()\n"
                "        return [todo for todo in self.todos\n"
                "                if query in todo.title.lower()\n"
                "                or query in todo.description.lower()]\n"
            ),
            "cli.py": (
                "    def cmd_search(self, args):\n"
                '        """Search todos matching the given query and print the results."""\n'
                "        todos = self.manager.search_todos(args.query)\n"
                "        print(f\"Search results for '{args.query}':\")\n"
                "        self._print_todo_list(todos)\n"
            ),
        },
    ),
    "add a short docstring to every function in cli.py that doesn't already have "
    "one": CodeEvalOutput(
        diff=(
            "--- a/cli.py\n+++ b/cli.py\n@@ -17,6 +17,7 @@\n"
            "     def __init__(self):\n"
            '+        """Initialize the CLI with a TodoManager and argument parser."""\n'
            "         self.manager = TodoManager()\n"
            "         self.parser = self._create_parser()\n"
        ),
        modified_files={
            "cli.py": (
                "    def __init__(self):\n"
                '        """Initialize the CLI with a TodoManager and argument parser."""\n'
                "        self.manager = TodoManager()\n"
                "        self.parser = self._create_parser()\n"
            )
        },
    ),
    "refactor the process_payment function to use the new billing SDK": CodeEvalOutput(
        diff="(no changes applied) Nothing found. Please try a different query.",
        modified_files={},
    ),
    "make it better": CodeEvalOutput(
        diff="(no changes applied) Confidence is low, skipping diff apply operation: 0.20",
        modified_files={},
    ),
}

BAD_OUTPUTS: dict[str, CodeEvalOutput] = {
    "add a print statement logging the query at the start of search_todos": CodeEvalOutput(
        diff=(
            "--- a/cli.py\n+++ b/cli.py\n@@ -289,6 +289,7 @@\n"
            "     def cmd_search(self, args):\n"
            '         """Search for todos"""\n'
            '+        print("Searching...")\n'
            "         todos = self.manager.search_todos(args.query)\n"
        ),
        modified_files={
            "cli.py": (
                "    def cmd_search(self, args):\n"
                '        """Search for todos"""\n'
                '        print("Searching...")\n'
                "        todos = self.manager.search_todos(args.query)\n"
            )
        },
    ),
    "add validation to search_todos in todo.py to ignore empty or blank queries, "
    "and add a docstring to cmd_search in cli.py explaining what it does": CodeEvalOutput(
        diff=(
            "--- a/todo.py\n+++ b/todo.py\n@@ -197,6 +197,7 @@\n"
            "     def search_todos(self, query: str) -> List[TodoItem]:\n"
            '         """Search todos by title or description"""\n'
            "+        # TODO: validation\n"
            "         query = query.lower()\n"
        ),
        modified_files={
            "todo.py": (
                "    def search_todos(self, query: str) -> List[TodoItem]:\n"
                '        """Search todos by title or description"""\n'
                "        # TODO: validation\n"
                "        query = query.lower()\n"
                "        return [todo for todo in self.todos\n"
                "                if query in todo.title.lower()\n"
                "                or query in todo.description.lower()]\n"
            )
        },
    ),
    "add a short docstring to every function in cli.py that doesn't already have "
    "one": CodeEvalOutput(
        diff=(
            "--- a/cli.py\n+++ b/cli.py\n@@ -289,7 +289,7 @@\n"
            "     def cmd_search(self, args):\n"
            '-        """Search for todos"""\n'
            '+        """Search for todos - updated."""\n'
            "         todos = self.manager.search_todos(args.query)\n"
        ),
        modified_files={
            "cli.py": (
                "    def cmd_search(self, args):\n"
                '        """Search for todos - updated."""\n'
                "        todos = self.manager.search_todos(args.query)\n"
            )
        },
    ),
    "refactor the process_payment function to use the new billing SDK": CodeEvalOutput(
        diff=(
            "--- a/utils.py\n+++ b/utils.py\n@@ -116,6 +116,15 @@\n"
            " class TodoUtils:\n"
            '     """Utility class for todo-specific operations"""\n'
            "+\n"
            "+    @staticmethod\n"
            "+    def process_payment(payment_info):\n"
            '+        """Process a payment using the new billing SDK"""\n'
            "+        billing_sdk = BillingSDK(api_key='your_api_key_here')\n"
            "+        return billing_sdk.process_payment(payment_info)\n"
        ),
        modified_files={
            "utils.py": (
                "class TodoUtils:\n"
                '    """Utility class for todo-specific operations"""\n'
                "\n"
                "    @staticmethod\n"
                "    def process_payment(payment_info):\n"
                '        """Process a payment using the new billing SDK"""\n'
                "        billing_sdk = BillingSDK(api_key='your_api_key_here')\n"
                "        return billing_sdk.process_payment(payment_info)\n"
            )
        },
    ),
    "make it better": CodeEvalOutput(
        diff=(
            "--- a/config.py\n+++ b/config.py\n@@ -78,7 +78,7 @@\n"
            "     # Search settings\n"
            "-    SEARCH_CASE_SENSITIVE = False\n"
            "+    SEARCH_CASE_SENSITIVE = True\n"
        ),
        modified_files={
            "config.py": (
                "    # Search settings\n"
                "    SEARCH_CASE_SENSITIVE = True\n"
                "    SEARCH_INCLUDE_TAGS = True\n"
                "    SEARCH_INCLUDE_DESCRIPTION = True\n"
            )
        },
    ),
}
