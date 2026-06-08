from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent


class ScopeAnalysis(BaseModel):
    scope_type: Literal["single", "multiple", "file", "project", "all"] = Field(
        description="The scope of changes requested by the user"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence level of the analysis (0.0 to 1.0)"
    )
    target_file: str | None = Field(
        default=None,
        description="Specific filename mentioned in the query, if any (e.g., 'main.py')",
    )
    target_functions: list[str] = Field(
        default_factory=list, description="List of specific function or class names mentioned"
    )
    intent_description: str = Field(
        description="Human-readable description of what the user wants to do"
    )
    suggested_top_k: int = Field(
        ge=1, le=100, description="Suggested number of code chunks to retrieve based on scope"
    )


class ScopeAnalyzer:
    def __init__(self, model: str):
        self.model = model
        self.agent = Agent(self.model, output_type=ScopeAnalysis, retries=3)

    async def analyze(self, query: str, codebase_stats: dict | None = None) -> ScopeAnalysis:
        stats_context = ""
        if codebase_stats and codebase_stats.get("total_chunks", 0) > 0:
            stats_context = f"""
**CODEBASE STATISTICS (use these to inform your suggested_top_k):**
- Total chunks in codebase: {codebase_stats['total_chunks']}
- Functions: {codebase_stats['chunks_by_type'].get('function', 0)}
- Classes: {codebase_stats['chunks_by_type'].get('class', 0)}
- Files and their chunk counts:
{chr(10).join(f'  - {f}: {c} chunks' for f, c in codebase_stats['chunks_by_file'].items())}

IMPORTANT: Use these REAL numbers to decide suggested_top_k:
- If targeting a specific file, cap top_k to that file's chunk count
- If targeting specific functions, use len(target_functions) + 2 as top_k
- Never suggest more chunks than actually exist in the target scope
"""

        system_prompt = f"""You are a code scope analyzer. Your job is to understand user queries about code modifications and determine the scope of changes.
{stats_context}
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
   - ALWAYS base this on the ACTUAL codebase statistics above when available
   - single: min(3, total_chunks) - just enough to find the target
   - multiple: len(target_functions) + 2 - targets plus small buffer
   - file: exact chunk count of target file (from stats above)
   - project/all: total_chunks or reasonable cap

**Important Guidelines:**
- Be language-agnostic: queries might be in English, Spanish, Portuguese, etc.
- Look for quantity indicators: "all", "every", "each", "todos", "todas", "每个", etc.
- Look for specificity: specific names = narrow scope, general terms = broad scope
- Consider context: "add logging" to one function vs "add logging" everywhere
- Default to "single" scope if ambiguous (safer to modify less)
- NEVER suggest more chunks than exist in the target scope

**Examples:**

Query: "add print statement to get_todo"
→ scope_type: "single", target_functions: ["get_todo"], suggested_top_k: 3

Query: "update get_todo and delete_todo to use async"
→ scope_type: "multiple", target_functions: ["get_todo", "delete_todo"], suggested_top_k: 4

Query: "add docstrings to every function in storage.py" (storage.py has 12 chunks)
→ scope_type: "file", target_file: "storage.py", suggested_top_k: 12

Query: "refactor all error handling across the codebase" (50 total chunks)
→ scope_type: "all", suggested_top_k: 50
"""

        user_message = f"""Analyze this query and return a structured scope analysis:

Query: {query}

Remember to:
1. Determine if this is single/multiple/file/project/all scope
2. Extract any specific filenames or function names
3. Provide a confidence score
4. Suggest an appropriate top_k value based on ACTUAL codebase statistics
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
                suggested_top_k=3,
            )
