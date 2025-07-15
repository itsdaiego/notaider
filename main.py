#!/usr/bin/env python3

from prompt_toolkit import PromptSession
import asyncio
from code_workflow import CodeWorkflow
from storage import Storage
from anthropic import Anthropic

import os
from typing import Optional
import numpy as np

GREEN = '\033[92m'

class NotAider:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"

        self.storage = Storage(storage_dir='db', app_dir='app')
        self._ensure_chunks_ready()

    def _ensure_chunks_ready(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, 'chunks_index.faiss')
            if not os.path.exists(chunks_index_path):
                print(f"{GREEN}Initializing code chunks database...")
                self.storage.store_code_chunks()
                print(f"{GREEN}Code chunks ready!")
        except Exception as e:
            print(f"{GREEN}Note: Could not initialize chunks database: {e}")

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

        storage = Storage(storage_dir='db', app_dir='app')
        try:
            results = storage.search_content(content, top_k=3)

            context = ""
            if results:
                for i, result in enumerate(results, 1):
                    if result['similarity'] > 0.4 or i == 1:
                        print(f'Including {result["filename"]} (similarity: {result["similarity"]:.3f})')
                        print(f'Result length: {len(result["content"])}')
                        context += f"\n{i}: {result['filename']} (similarity: {result['similarity']:.2f}):\n"
                        context += f"{result['content'][:5000]}{'...' if len(result['content']) > 1500 else ''}\n"

            if context:
                user_message = f"User query: {content}\n\nRelevant file content:{context}\n\nPlease analyze the code and provide a direct answer to the user's query using the provided context."
            else:
                user_message = f"Please enhance this prompt: {content}"

        except Exception as e:
            print(f"Note: Could not access embeddings database: {str(e)}")
            user_message = f"Please enhance this prompt: {content}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                return getattr(content_block, 'text', str(content_block))
            return "No content in response"
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
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )

            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                return getattr(content_block, 'text', str(content_block))
            return "No content in response"
        except Exception as e:
            return f"Error processing request: {str(e)}"


async def main():
    session = PromptSession()

    print(f"{GREEN}Welcome to NotAider CLI with Dynamic Code Workflow!")
    print(f"{GREEN}Commands:")
    print(f"{GREEN}  /ask <prompt>          - Enhance and process prompt")
    print(f"{GREEN}  /add <pattern>         - Add files to vector database")
    print(f"{GREEN}  /code <request>        - AI-powered code modification with preview")
    print(f"{GREEN}Type 'exit' or press Ctrl+D to quit.")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    while True:
        try:
            command = (await session.prompt_async("notaider> ")).strip()

            if not command:
                continue

            if command.lower() in ['exit', 'quit']:
                break

            storage = Storage(storage_dir='db', app_dir='app')

            if command.startswith('/ask '):
                content = command[5:].strip()
                if not content:
                    print(f"{GREEN}Usage: /ask <your prompt>")
                    continue

                if not api_key:
                    print(f"{GREEN}Error: ANTHROPIC_API_KEY environment variable not set")
                    print(f"{GREEN}Please set your API key: export ANTHROPIC_API_KEY='your-key-here'")
                    continue

                print(f"{GREEN}{'='*29}")
                print(f"{GREEN}Enhancing your prompt...")
                print(f"{GREEN}{'='*29}")

                try:
                    notaider = NotAider(api_key)
                    enhanced = await notaider.enhance_prompt(content)
                    print(f"{GREEN}{'='*29}")
                    print(f"{GREEN}Enhanced Prompt:")
                    print(f"{GREEN}{'='*29}")
                    print(f"{GREEN}{enhanced}")
                    print(f"{GREEN}{'='*29}")
                    print(f"{GREEN}Generating Final Response:")
                    print(f"{GREEN}{'='*29}")
                    if enhanced.startswith("Error"):
                        print(f"{GREEN}{enhanced}")
                        continue

                    output = await notaider.process_request(enhanced)

                    if output and output.startswith("Error"):
                        print(f"{GREEN}{output}")
                    else:
                        print(f"{GREEN}{output}")

                except Exception as e:
                    print(f"{GREEN}Error initializing NotAider: {str(e)}")

            elif command.startswith('/add'):
                content = str(command[5:].strip())

                filenames, new_files = storage.store_files(content)

                if not new_files:
                    print(f"{GREEN}No files added.")
                else:
                    print(f"{GREEN}Files added:")
                    for file in filenames:
                        print(f"{GREEN}{file}")

            elif command.startswith('/code '):
                content = command[6:].strip()
                if not content:
                    print(f"{GREEN}Usage: /code <your code>")
                    print(f"{GREEN}Example: /code Add None checks to the add_todo function")
                    continue

                if not api_key:
                    print(f"{GREEN}Error: ANTHROPIC_API_KEY environment variable not set")
                    print(f"{GREEN}Please set your API key: export ANTHROPIC_API_KEY='your-key-here'")
                    continue

                try:
                    notaider = NotAider(api_key)
                    code_workflow = CodeWorkflow(
                        storage=notaider.storage,
                        model=notaider.model,
                        client=notaider.client
                    )
                    result = await code_workflow.perform_diff(content)
                    print(result)
                except Exception as e:
                    print(f"{GREEN}Error in code workflow: {str(e)}")

            else:
                print(f"{GREEN}your command is invalid: {command}")
                print(f"{GREEN}Possible commands:")
                print(f"{GREEN}  /ask <prompt>          - Enhance and process prompt")
                print(f"{GREEN}  /add <pattern>         - Add files to vector database")
                print(f"{GREEN}  /code <request>        - AI-powered code modification with preview")
                print(f"{GREEN}  exit/quit              - Exit the program")

        except (KeyboardInterrupt, EOFError):
            print(f"{GREEN}Bye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
