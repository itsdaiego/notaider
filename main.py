#!/usr/bin/env python3

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import Lexer
import asyncio
from code_workflow import CodeWorkflow
from colors import Colors
from storage import Storage
from pydantic_ai import Agent

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Enable debugpy only when ENABLE_DEBUGPY is set
if os.getenv("ENABLE_DEBUGPY", "0") == "1":
    import debugpy
    debugpy_host = os.getenv("DEBUGPY_HOST", "0.0.0.0")
    debugpy_port = int(os.getenv("DEBUGPY_PORT", "5678"))
    print(f"🐛 Debug mode enabled - listening on {debugpy_host}:{debugpy_port}")
    debugpy.listen((debugpy_host, debugpy_port))

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
    def __init__(self, api_key: str):
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")
        self.client = Agent(self.model)

        self.storage = Storage(
            storage_dir=os.getenv("STORAGE_DIR", "db"),
            app_dir=os.getenv("APP_DIR", "app")
        )
        self._ensure_chunks_ready()

    def _ensure_chunks_ready(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, 'chunks_index.faiss')
            if not os.path.exists(chunks_index_path):
                os.path.join(self.storage.storage_dir, 'chunks_index.faiss')
        except Exception as e:
            print(f"{Colors.GREEN}Note: Could not initialize chunks database: {e}")

    async def enhance_prompt(self, content: str) -> str:
        system_prompt = """You are an AI assistant that analyzes code and provides direct answers based on the provided file context.

When given a user query and relevant file content, your task is to:
1. First, check if the provided context contains the information needed to answer the query directly
2. If yes, provide a direct answer using the code content
3. If no, then enhance the prompt with the available context

Guidelines:
- If the user asks about methods, functions, classes, or specific code elements and the context contains that information, provide a direct code analysis
- Use the actual code content to answer questions about implementation details
- When context is available, prioritize answering the question directly over prompt enhancement
- Only fall back to prompt enhancement when the context doesn't contain the requested information"""

        storage = Storage(
            storage_dir=os.getenv("STORAGE_DIR", "db"),
            app_dir=os.getenv("APP_DIR", "app")
        )
        try:
            results = storage.search_content(content, top_k=3)
            MAX_FILE_CHAR_SIZE = 1500

            similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
            context = ""
            if results:
                for i, result in enumerate(results, 1):
                    if result['similarity'] > similarity_threshold or i == 1:
                        print(f'Including {result["filename"]} (similarity: {result["similarity"]:.3f})')
                        print(f'Result length: {len(result["content"])}')
                        context += f"\n{i}: {result['filename']} (similarity: {result['similarity']:.2f}):\n"
                        context += f"{result['content'][:MAX_FILE_CHAR_SIZE]}\n"

            if context:
                user_message = f"User query: {content}\n\nRelevant file content:{context}\n\nPlease analyze the code and provide a direct answer to the user's query using the provided context."
            else:
                # TODO: this shouldnt be needed once we allow for tool calls 
                # therefore allowing notaider to find additional information
                # during inference time
                user_message = f"Please enhance this prompt: {content}"

        except Exception as e:
            print(f"Note: Could not access embeddings database: {str(e)}")
            user_message = f"Please enhance this prompt: {content}"

        try:
            response = await self.client.run(f"{system_prompt}\n\n{user_message}")
            return str(response)
        except Exception as e:
            return f"Error enhancing prompt: {str(e)}"


    async def process_request(self, content: str) -> Optional[str]:
        system_prompt = """You are an AI assistant that is designed to answer questions about programming, technology, and general knowledge.
        Your task is to provide the best response to the user, and generate code according to the user's request.
        the format should be like this:

        ```python
        <your code here>
        ```

        Guidelines:
- Provide clear, concise answers
- Use examples where helpful
- Maintain a friendly and professional tone
- Avoid unnecessary jargon
- Provide the output as markdown code blocks when applicable
"""

        try:
            response = await self.client.run(content)
            return str(response.data)
        except Exception as e:
            return f"Error processing request: {str(e)}"


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
    kb = KeyBindings()

    @kb.add('escape')
    def _(event):
        if event.current_buffer.text:
            event.current_buffer.reset()
        else:
            event.app.exit()

    completer = WordCompleter(['@ask', '@add', '@code', "@list", 'exit', 'quit'], ignore_case=True, sentence=True)

    style = Style.from_dict({
        'completion-menu.completion': 'bg:#424242 #ffffff',
        'completion-menu.completion.current': 'bg:#1b5e20 #ffffff bold',
        'completion-menu': 'bg:#424242',
        'command': 'bg:#424242 #ffffff',
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
    print(f"{Colors.GREEN}Commands:")
    print(f"{Colors.GREEN}  @ask <prompt>          - Enhance and process prompt")
    print(f"{Colors.GREEN}  @add <pattern>         - Add files to vector database")
    print(f"{Colors.GREEN}  @list <request>        - List indexed files")
    print(f"{Colors.GREEN}  @code <request>        - AI-powered code modification with preview")
    print(f"{Colors.GREEN}Type 'exit' or press Ctrl+D to quit.")

    api_key = os.getenv("OPENAI_API_KEY") or ""

    while True:
        try:
            result = await session.prompt_async("notaider> ")
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
                    print(f"{Colors.GREEN}Usage: @ask <your prompt>")
                    continue

                if not api_key:
                    print(f"{Colors.GREEN}Error: OPENAI_API_KEY environment variable not set")
                    print(f"{Colors.GREEN}Please set your API key: export OPENAI_API_KEY='your-key-here'")
                    continue

                print(f"{Colors.GREEN}{'='*29}")
                print(f"{Colors.GREEN}Enhancing your prompt...")
                print(f"{Colors.GREEN}{'='*29}")

                try:
                    notaider = NotAider(api_key)
                    enhanced = await notaider.enhance_prompt(content)

                    print(f"{Colors.GREEN}{enhanced}")

                except Exception as e:
                    print(f"{Colors.GREEN}Error initializing NotAider: {str(e)}")

            elif command.startswith('@add'):
                content = str(command[5:].strip())

                filenames, new_files = storage.store_files(content)

                if not new_files:
                    print(f"{Colors.GREEN}No files added.")
                else:
                    print(f"{Colors.GREEN}Files added:")
                    for file in filenames:
                        print(f"{Colors.GREEN}{file}")

            elif command.startswith('@list'):
                try:
                    notaider = NotAider(api_key=api_key)
                    files = notaider.storage.list_indexed_files()
                    if files:
                        print(f"{Colors.GREEN}Indexed files:")
                        for file in files:
                            print(f"{Colors.GREEN}{file}")
                    else:
                        print(f"{Colors.GREEN}No files indexed yet.")
                except Exception as e:
                    print(f"{Colors.GREEN}Error listing files: {str(e)}")

            elif command.startswith('@code '):
                content = command[6:].strip()
                if not content:
                    print(f"{Colors.GREEN}Usage: @code <your request>")
                    print(f"{Colors.GREEN}Example: @code Add None checks to the add_todo function")
                    print(f"{Colors.GREEN}Example: @code Add error handling to every function in main.py")
                    continue

                if not api_key:
                    print(f"{Colors.GREEN}Error: OPENAI_API_KEY environment variable not set")
                    print(f"{Colors.GREEN}Please set your API key: export OPENAI_API_KEY='your-key-here'")
                    continue

                try:
                    notaider = NotAider(api_key)
                    code_workflow = CodeWorkflow(
                        storage=notaider.storage,
                        model=notaider.model,
                        client=notaider.client
                    )
                    result_message = await code_workflow.perform_diff(content)
                    print(f"{result_message}" if result_message else "")
                except Exception as e:
                    print(f"{Colors.GREEN}Error in code workflow: {str(e)}")

            else:
                print(f"{Colors.GREEN}your command is invalid: {command}")
                print(f"{Colors.GREEN}Possible commands:")
                print(f"{Colors.GREEN}  @ask <prompt>          - Enhance and process prompt")
                print(f"{Colors.GREEN}  @add <pattern>         - Add files to vector database")
                print(f"{Colors.GREEN}  @code <request>        - AI-powered code modification with preview")
                print(f"{Colors.GREEN}  exit/quit              - Exit the program")

        except (KeyboardInterrupt, EOFError):
            print(f"{Colors.GREEN}Bye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
