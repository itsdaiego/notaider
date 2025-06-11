#!/usr/bin/env python3

from prompt_toolkit import PromptSession
import asyncio
from storage import Storage
from anthropic import Anthropic
import os
from typing import Optional

# ANSI color codes
GREEN = '\033[92m'

class NotAider:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"
    
    async def enhance_prompt(self, content: str) -> str:
        system_prompt = """You are an AI assistant that enhances and improves user prompts to make them more effective for AI interactions. 
Your task is to take the user's input and rewrite it to be clearer, more specific according to the knowledge base, and more likely to get a high-quality response.

Guidelines:
- Make prompts more specific and actionable
- Structure requests clearly
- Maintain the original intent
- Keep it concise but comprehensive
- Use the additional context from the knowledge base to enhance the prompt"""

        storage = Storage(storage_dir='db', app_dir='app')
        try:
            results = storage.search_content(content, top_k=3)

            context = ""
            if results:
                for i, result in enumerate(results, 1):
                    if result['similarity'] > 0.7: # threshold of similarity
                        print(f'HEY YO {result["similarity"]}')
                        context += f"\n{i}: {result['filename']} (similarity: {result['similarity']:.2f}):\n"
                        context += f"{result['content'][:500]}{'...' if len(result['content']) > 500 else ''}\n"

            user_message = f"Please enhance this prompt: {content}{context}"

        except Exception as e:
            # Fallback to original behavior if embeddings not available
            print(f"Note: Could not access embeddings database: {str(e)}")
            user_message = f"Please enhance this prompt: {content}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,  # Increased to handle context
                system=system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": user_message
                    }
                ]
            )
            return response.content[0].text
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
- Don't write any unnecessary comments in the code
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

            return response.content[0].text
        except Exception as e:
            return f"Error processing request: {str(e)}"

async def main():
    session = PromptSession()

    print(f"{GREEN}Welcome to NotAider CLI!")
    print(f"{GREEN}Type '/ask <your prompt>' to enhance your prompt for AI interactions.")
    print(f"{GREEN}Type 'exit' or press Ctrl+D to quit.")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    while True:
        try:
            command = (await session.prompt_async("notaider> ")).strip()

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
                storage = Storage(storage_dir='db', app_dir='app')
                filenames = storage.store_files()

                print(f"{GREEN}Files added:")
                for file in filenames:
                    print(f"{GREEN}{file}")
            else:
                print(f"{GREEN}your command is invalid: {command}")
                print(f"{GREEN}Possible commands: /ask, /add <your_prompt>")
            
        except (KeyboardInterrupt, EOFError):
            print(f"{GREEN}Bye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
