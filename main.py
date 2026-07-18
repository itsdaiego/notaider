#!/usr/bin/env python3

import asyncio
import os
import uuid

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from pydantic_ai import Agent

from code_workflow import CodeWorkflow
from colors import Colors
from observability import init_observability, trace_session
from storage import Storage

load_dotenv()
init_observability()

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def _print_logo():
    logo = f"""

    {Colors.LOGO_GREEN}{Colors.BOLD}
        ███╗   ██╗ ██████╗ ████████╗ █████╗ ██╗██████╗ ███████╗██████╗
        ████╗  ██║██╔═══██╗╚══██╔══╝██╔══██╗██║██╔══██╗██╔════╝██╔══██╗
    {Colors.NEON_GREEN}    ██╔██╗ ██║██║   ██║   ██║   ███████║██║██║  ██║█████╗  ██████╔╝
    {Colors.ACCENT_GREEN}    ██║╚██╗██║██║   ██║   ██║   ██╔══██║██║██║  ██║██╔══╝  ██╔══██╗
    {Colors.EMERALD_GREEN}    ██║ ╚████║╚██████╔╝   ██║   ██║  ██║██║██████╔╝███████╗██║  ██║
        ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
    """
    print(logo)


class NotAider:
    def __init__(self, api_key: str, storage: Storage | None = None):
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")
        self.storage = storage or Storage(
            storage_dir=os.getenv("STORAGE_DIR", "db"),
            app_dir=os.getenv("APP_DIR", "app")
        )
        self.client = self._build_agent()

    def _build_agent(self) -> Agent:
        agent = Agent(
            self.model,
            system_prompt=(
                "You are an AI assistant that answers questions about a codebase. "
                "Use the search_code tool to find relevant code before answering. "
                "Search multiple times with different queries if needed. "
                "Reference actual function names, class names, and line numbers. "
                "Never give vague instructions — answer concretely using the code you find."
            ),
            instrument=True,
        )

        storage = self.storage

        @agent.tool_plain
        def search_code(query: str) -> str:
            """Search the codebase for code chunks relevant to a query."""
            print(f"{Colors.MUTED}  [tool] search_code({query!r})")
            return storage.format_search_results(query)

        @agent.tool_plain
        def run_command(command: str) -> str:
            """Run a bash command in the project directory (e.g. grep, find, cat)."""
            print(f"{Colors.MUTED}  [tool] run_command({command!r})")
            return storage.run_command(command)

        return agent

    async def enhance_prompt(self, content: str) -> str:
        try:
            response = await self.client.run(content)
            return str(response.output)
        except Exception as e:
            return f"Error: {str(e)}"


class CommandLexer(Lexer):
    def lex_document(self, document):
        def get_line(lineno):
            text = document.lines[lineno]
            tokens = []
            i = 0
            while i < len(text):
                if text[i] == '@' and i == 0:
                    end = i + 1
                    while end < len(text) and text[end] not in (' ', '\t', '\n'):
                        end += 1
                    tokens.append(('class:command', text[i:end]))
                    i = end
                else:
                    start = i
                    while i < len(text) and not (text[i] == '@' and i == 0):
                        i += 1
                    if i > start:
                        tokens.append(('', text[start:i]))
            return tokens
        return get_line

async def main():
    session_id = str(uuid.uuid4())
    kb = KeyBindings()

    @kb.add('escape')
    def _(event):
        if event.current_buffer.text:
            event.current_buffer.reset()
        else:
            event.app.exit()

    completer = WordCompleter(['@ask', '@add', '@code', "@list", 'exit', 'quit'], ignore_case=True, sentence=True)

    style = Style.from_dict({
        'completion-menu.completion': 'bg:#1a2e1a #87d787',
        'completion-menu.completion.current': 'bg:#005f00 #00ff87 bold',
        'completion-menu': 'bg:#1a2e1a',
        'command': '#00ff87 bold',
        'prompt': '#00ff87 bold',
    })

    session = PromptSession(
        key_bindings=kb,
        completer=completer,
        complete_while_typing=True,
        style=style,
        lexer=CommandLexer()
    )

    _print_logo()
    print()
    print(f"{Colors.HEADER}Commands:")
    print(f"{Colors.HEADER}  @ask{Colors.MUTED}   <prompt>   - Enhance and process prompt")
    print(f"{Colors.HEADER}  @add{Colors.MUTED}   <pattern>  - Add files to vector database")
    print(f"{Colors.HEADER}  @list{Colors.MUTED}  <request>  - List indexed files")
    print(f"{Colors.HEADER}  @code{Colors.MUTED}  <request>  - AI-powered code modification with preview")
    print(f"{Colors.MUTED}Type 'exit' or press Ctrl+D to quit.{Colors.RESET}")

    api_key = os.getenv("OPENAI_API_KEY") or ""

    while True:
        try:
            result = await session.prompt_async([('class:prompt', 'notaider> ')])
            if result is None:
                break
            command = result.strip()

            if not command:
                continue

            if command.lower() in ['exit', 'quit']:
                break

            storage = Storage(
                storage_dir=os.getenv("STORAGE_DIR", "db"),
                app_dir=os.getenv("APP_DIR", "app")
            )

            if command.startswith('@ask '):
                content = command[5:].strip()
                if not content:
                    print(f"{Colors.MUTED}Usage: @ask <your prompt>")
                    continue

                if not api_key:
                    print(f"{Colors.ERROR}Error: OPENAI_API_KEY environment variable not set")
                    print(f"{Colors.MUTED}Please set your API key: export OPENAI_API_KEY='your-key-here'")
                    continue

                print(f"{Colors.HEADER}{'='*29}")
                print(f"{Colors.INFO}Enhancing your prompt...")
                print(f"{Colors.HEADER}{'='*29}")

                try:
                    notaider = NotAider(api_key)
                    with trace_session(session_id, tags=["ask"], name="ask"):
                        enhanced = await notaider.enhance_prompt(content)

                    print(f"{Colors.INFO}{enhanced}")

                except Exception as e:
                    print(f"{Colors.ERROR}Error initializing NotAider: {str(e)}")

            elif command.startswith('@add'):
                content = str(command[5:].strip())

                filenames, new_files = storage.store_files(content)

                if not new_files:
                    print(f"{Colors.MUTED}No files added.")
                else:
                    storage.store_code_chunks(content)
                    print(f"{Colors.SUCCESS}Files added:")
                    for file in filenames:
                        print(f"{Colors.MUTED}  {file}")

            elif command.startswith('@list'):
                try:
                    notaider = NotAider(api_key=api_key)
                    files = notaider.storage.list_indexed_files()
                    if files:
                        print(f"{Colors.HEADER}Indexed files:")
                        for file in files:
                            print(f"{Colors.MUTED}  {file}")
                    else:
                        print(f"{Colors.MUTED}No files indexed yet.")
                except Exception as e:
                    print(f"{Colors.ERROR}Error listing files: {str(e)}")

            elif command.startswith('@code'):
                content = command[6:].strip()
                if not content:
                    print(f"{Colors.MUTED}Usage: @code <your request>")
                    print(f"{Colors.MUTED}Example: @code Add None checks to the add_todo function")
                    print(f"{Colors.MUTED}Example: @code Add error handling to every function in main.py")
                    continue

                if not api_key:
                    print(f"{Colors.ERROR}Error: OPENAI_API_KEY environment variable not set")
                    print(f"{Colors.MUTED}Please set your API key: export OPENAI_API_KEY='your-key-here'")
                    continue

                try:
                    notaider = NotAider(api_key)
                    code_workflow = CodeWorkflow(
                        storage=notaider.storage,
                        model=notaider.model,
                    )
                    with trace_session(session_id, tags=["code"], name="code"):
                        result_message = await code_workflow.perform_diff(content)
                    print(f"{result_message}" if result_message else "")
                except Exception as e:
                    print(f"{Colors.ERROR}Error in code workflow: {str(e)}")

            else:
                print(f"{Colors.ERROR}Invalid command: {command}")
                print(f"{Colors.MUTED}Possible commands:")
                print(f"{Colors.MUTED}  @ask <prompt>   - Enhance and process prompt")
                print(f"{Colors.MUTED}  @add <pattern>  - Add files to vector database")
                print(f"{Colors.MUTED}  @code <request> - AI-powered code modification with preview")
                print(f"{Colors.MUTED}  exit/quit       - Exit the program")

        except (KeyboardInterrupt, EOFError):
            print(f"{Colors.MUTED}Bye!{Colors.RESET}")
            break


if __name__ == "__main__":
    asyncio.run(main())
