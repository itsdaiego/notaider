#!/usr/bin/env python3

from prompt_toolkit import PromptSession
import asyncio
import logging
from anthropic import Anthropic
import os
from typing import Optional


class NotAider:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"
    
    async def enhance_prompt(self, content: str) -> str:
        system_prompt = """You are an AI assistant that enhances and improves user prompts to make them more effective for AI interactions. 
Your task is to take the user's input and rewrite it to be clearer, more specific, and more likely to get a high-quality response.

Guidelines:
- Make prompts more specific and actionable
- Add context where helpful
- Structure requests clearly
- Maintain the original intent
- Keep it concise but comprehensive"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": f"Please enhance this prompt: {content}"
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
    logger = logging.getLogger("notaider")

    print("Welcome to NotAider CLI!")
    print("Type '/ask <your prompt>' to enhance your prompt for AI interactions.")
    print("Type 'exit' or press Ctrl+D to quit.")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    while True:
        try:
            command = (await session.prompt_async("notaider> ")).strip()

            if command.startswith('/ask '):
                content = command[5:].strip()
                if not content:
                    print("Usage: /ask <your prompt>")
                    continue
                
                if not api_key:
                    print("Error: ANTHROPIC_API_KEY environment variable not set")
                    print("Please set your API key: export ANTHROPIC_API_KEY='your-key-here'")
                    continue

                print("#############################")
                print("Enhancing your prompt...")
                print("#############################")
                
                try:
                    notaider = NotAider(api_key)
                    enhanced = await notaider.enhance_prompt(content)
                    print("#############################")
                    print("Enhanced Prompt:")
                    print("#############################")
                    print(enhanced)
                    print("#############################")
                    print("Generating Final Response:")
                    print("#############################")
                    if enhanced.startswith("Error"):
                        print(enhanced)
                        continue

                    output = await notaider.process_request(enhanced)
                    
                    if output and output.startswith("Error"):
                        print(output)

                    
                    print(output)
                except Exception as e:
                    print(f"Error initializing NotAider: {str(e)}")
            print("your command entered:", command)
        except EOFError:
            logger.info("Someone pressed Ctrl+D, exiting...")
            break


if __name__ == "__main__":
    asyncio.run(main())
