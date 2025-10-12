import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


class ScopeAnalysis(BaseModel):
    scope_type: Literal["single", "multiple", "file", "project", "all"] = Field(
        description="The scope of changes requested by the user"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of the analysis (0.0 to 1.0)"
    )
    target_file: str | None = Field(
        default=None,
        description="Specific filename mentioned in the query, if any (e.g., 'main.py')"
    )
    target_functions: list[str] = Field(
        default_factory=list,
        description="List of specific function or class names mentioned"
    )
    intent_description: str = Field(
        description="Human-readable description of what the user wants to do"
    )
    suggested_top_k: int = Field(
        ge=1,
        le=100,
        description="Suggested number of code chunks to retrieve based on scope"
    )


class ScopeAnalyzer:
    def __init__(self):
        self.model = os.getenv("AI_MODEL", "claude-3-5-haiku-20241022")
        self.agent = Agent(self.model, output_type=ScopeAnalysis, retries=3)

    async def analyze(self, query: str) -> ScopeAnalysis:
        system_prompt = """You are a code scope analyzer. Your job is to understand user queries about code modifications and determine the scope of changes.

Analyze the user's query and determine:

1. **scope_type**: The breadth of changes requested
   - "single": User wants to modify ONE specific function/class (e.g., "add logging to get_user")
   - "multiple": User wants to modify SEVERAL specific items (e.g., "update validate_input and sanitize_data")
   - "file": User wants to modify ALL matching items in ONE file (e.g., "add docstrings to all functions in auth.py")
   - "project": User wants to modify ALL matching items across MULTIPLE files (e.g., "add type hints to all functions")
   - "all": User wants to modify EVERYTHING that matches (e.g., "refactor all error handling")

2. **confidence**: How confident you are in this analysis (0.0 to 1.0)
   - High (0.8-1.0): Query is clear and specific
   - Medium (0.5-0.79): Query is somewhat ambiguous
   - Low (0.0-0.49): Query is very vague or unclear

3. **target_file**: Extract any specific filename mentioned
   - Look for patterns like "in auth.py", "the main.py file", "storage module"
   - Return just the filename (e.g., "auth.py"), not the full path
   - Return None if no specific file is mentioned

4. **target_functions**: Extract specific function or class names mentioned
   - Look for identifiers that look like code names (snake_case, camelCase, etc.)
   - Examples: "get_user", "UserModel", "validate_input"

5. **intent_description**: A clear, concise summary of what the user wants
   - Example: "Add error logging to the authentication function"
   - Example: "Update all database query functions to use async/await"

6. **suggested_top_k**: How many code chunks to retrieve
   - single: 3-5 chunks (to ensure we get the right one)
   - multiple: 5-15 chunks (depending on how many targets)
   - file: 10-50 chunks (all functions in a file)
   - project/all: 20-100 chunks (broad scope)

**Important Guidelines:**
- Be language-agnostic: queries might be in English, Spanish, Portuguese, etc.
- Look for quantity indicators: "all", "every", "each", "todos", "todas", "每个", etc.
- Look for specificity: specific names = narrow scope, general terms = broad scope
- Consider context: "add logging" to one function vs "add logging" everywhere
- Default to "single" scope if ambiguous (safer to modify less)

**Examples:**

Query: "add print statement to get_todo"
→ scope_type: "single", target_functions: ["get_todo"], suggested_top_k: 3

Query: "update get_todo and delete_todo to use async"
→ scope_type: "multiple", target_functions: ["get_todo", "delete_todo"], suggested_top_k: 10

Query: "add docstrings to every function in storage.py"
→ scope_type: "file", target_file: "storage.py", suggested_top_k: 30

Query: "refactor all error handling across the codebase"
→ scope_type: "all", suggested_top_k: 50

Query: "añadir logs a todas las funciones en auth.py"
→ scope_type: "file", target_file: "auth.py", suggested_top_k: 30
"""

        user_message = f"""Analyze this query and return a structured scope analysis:

Query: {query}

Remember to:
1. Determine if this is single/multiple/file/project/all scope
2. Extract any specific filenames or function names
3. Provide a confidence score
4. Suggest an appropriate top_k value
5. Write a clear intent description"""

        try:
            response = await self.agent.run(f"{system_prompt}\n\n{user_message}")
            return response.output
        except Exception as e:
            return ScopeAnalysis(
                scope_type="single",
                confidence=0.1,
                target_file=None,
                target_functions=[],
                intent_description=f"Failed to analyze query: {str(e)}",
                suggested_top_k=3
            )
