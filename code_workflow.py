import difflib
import os
from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent, AgentRunResult, ModelRetry

from colors import Colors
from scope_analyzer import ScopeAnalysis, ScopeAnalyzer
from storage import SearchedCodeChunk, Storage

load_dotenv()


def _colorize_diff(diff: str) -> str:
    """Colorize unified diff output with green/red shading."""
    lines = []
    for line in diff.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            lines.append(f"{Colors.DIFF_ADD}{line}{Colors.RESET}")
        elif line.startswith('-') and not line.startswith('---'):
            lines.append(f"{Colors.DIFF_DEL}{line}{Colors.RESET}")
        elif line.startswith('@@'):
            lines.append(f"{Colors.DIFF_META}{line}{Colors.RESET}")
        elif line.startswith('+++') or line.startswith('---'):
            lines.append(f"{Colors.HEADER}{line}{Colors.RESET}")
        else:
            lines.append(f"{Colors.MUTED}{line}{Colors.RESET}")
    return '\n'.join(lines)


class CodeChunkChange(BaseModel):
    old_code: str
    new_code: str
    filename: str
    chunk_name: str


class CodeWorkflowOutput(BaseModel):
    changes: list[CodeChunkChange]


@dataclass
class CodeChange:
    old_code: str
    new_code: str
    filename: str
    chunk_name: str


class CodeWorkflow:
    def __init__(self, storage: Storage, model):
        self.storage = storage
        self.model = model
        self.scope_analyzer = ScopeAnalyzer(model)

    def _check_code_chunks(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, "chunks_index.faiss")
            if not os.path.exists(chunks_index_path):
                print(f"{Colors.INFO}Initializing code chunks database...")
                self.storage.store_code_chunks()
                print(f"{Colors.SUCCESS}Code chunks ready!")
        except Exception as e:
            print(f"{Colors.MUTED}Note: Could not initialize chunks database: {e}")

    def _build_chunk_context(self, code_chunks: list[SearchedCodeChunk]) -> list[str]:
        context_chunks = []
        for i, c in enumerate(code_chunks, 1):
            ce_score = c.get("cross_encoder_score", 0)
            context_chunks.append(
                f"Chunk #{i} (relevance: {ce_score:.3f}, HIGHEST MATCH)"
                if i == 1
                else f"Chunk #{i} (relevance: {ce_score:.3f})"
            )
            context_chunks.append(f"  - Type: {c['type']}")
            context_chunks.append(f"  - Name: {c['name']}")
            context_chunks.append(f"  - File: {c['filename']}")

            # Calculate indentation level for emphasis
            code_lines = c["code"].split("\n")
            first_line = code_lines[0] if code_lines else ""
            indent_spaces = len(first_line) - len(first_line.lstrip(" "))

            context_chunks.append(
                f"  - Indentation: {indent_spaces} spaces (MUST BE PRESERVED EXACTLY)"
            )
            context_chunks.append(f"  - Code:\n{c['code']}")
            context_chunks.append("")

        return context_chunks

    async def _adjust_instructions(self, query: str, scope: ScopeAnalysis, context_chunks: list[str], chunk_count: int, chunk_names: set[str] | None = None) -> AgentRunResult[CodeWorkflowOutput]:
        if scope.scope_type in ["file", "project", "all"]:
            scope_instruction = f"""
        SCOPE: The user wants to modify {scope.intent_description}.
        This is a BROAD scope ({scope.scope_type}) - you MUST return modifications for ALL {chunk_count} chunks provided below.
        Each chunk should receive the modification requested by the user.
        """
        elif scope.scope_type == "multiple":
            targets = ', '.join(scope.target_functions) if scope.target_functions else 'infer from query'
            scope_instruction = f"""
        SCOPE: The user wants to modify {scope.intent_description}.
        This is a MULTIPLE scope - you MUST return exactly {len(scope.target_functions)} CodeChunkChange entries, one for EACH of these targets: {targets}
        Find the chunk that matches each target and return the modified code for it.
        Do NOT skip any target. Every target listed above MUST appear in your changes list.
        """
        else:
            target_hint = (
                f"\n        Target function/class: {', '.join(scope.target_functions)}"
                if scope.target_functions
                else ""
            )
            scope_instruction = f"""
        SCOPE: The user wants to modify {scope.intent_description}.
        This is a SINGLE scope - only modify the chunk that best matches the user's request (typically Chunk #1).{target_hint}
        """

        transformation_prompt = f"""
        Here are the code chunks ranked by relevance to the user's request.

        {"\n".join(context_chunks)}

        User request: {query}

        {scope_instruction}

        CRITICAL INSTRUCTIONS:
        1. Read the SCOPE section above carefully to understand how many chunks to modify
        2. Use SEARCH/REPLACE format: specify the exact lines to find and what to replace them with
        3. Do NOT reproduce the entire function — only include the lines that change plus minimal context

        Return a CodeWorkflowOutput with a changes list. For EACH modification, add a CodeChunkChange with:
        - old_code: the EXACT lines from the original code to replace. Copy them character-for-character from the chunks above, including all indentation and whitespace. Include enough surrounding lines to make the match unique within the file. old_code must NEVER be empty when modifying existing code.
        - new_code: the replacement lines, preserving the same indentation as old_code.
        - filename: the filename of that chunk (e.g., "todo.py")
        - chunk_name: the name of the function/class being modified, or the new name if adding

        RULES:
        - old_code must ALWAYS contain the original lines you are replacing. It must be a non-empty, exact substring of the code shown above.
        - The ONLY case where old_code can be "" is when creating an entirely new function or a new file that does not exist yet.
        - Keep old_code minimal — just the lines around the edit point, not the whole function.
        - new_code must preserve the exact same indentation as old_code.

        EXAMPLE - Adding a variable to an existing function:
        If the original code is:
            def main():
                print("hello")
        And you want to add `x = 42` after the def line, you return:
            old_code: "def main():\n    print(\"hello\")"
            new_code: "def main():\n    x = 42\n    print(\"hello\")"
        NOT old_code: "" — that would append to the file instead of inserting into the function.
        """

        ai_model = os.getenv("AI_MODEL", "gpt-4o-mini")
        agent = Agent(ai_model, output_type=CodeWorkflowOutput, retries=8, instrument=True)

        @agent.tool_plain
        def search_code(query: str) -> str:
            """Search the codebase for code chunks relevant to a query."""
            print(f"{Colors.MUTED}  [tool] search_code({query!r})")
            return self.storage.format_search_results(query)

        @agent.tool_plain
        def run_command(command: str) -> str:
            """Run a bash command in the project directory (e.g. grep, find, cat)."""
            print(f"{Colors.MUTED}  [tool] run_command({command!r})")
            return self.storage.run_command(command)

        @agent.output_validator
        async def validate_changes(result: CodeWorkflowOutput) -> CodeWorkflowOutput:
            if not chunk_names:
                return result
            invalid = [
                c.chunk_name for c in result.changes
                if not c.old_code.strip() and c.chunk_name in chunk_names
            ]
            if invalid:
                raise ModelRetry(
                    f"old_code must not be empty when modifying existing code. "
                    f"These chunks need non-empty old_code: {', '.join(invalid)}. "
                    f"Copy the exact lines from the original code that you want to replace."
                )
            return result

        try:
            response = await agent.run(transformation_prompt)
        except ValidationError as ve:
            raise Exception(f"Error in AI response validation: {ve}")
        except Exception as e:
            raise Exception(f"Error in AI response: {e}")

        if not response.output or not response.output.changes:
            raise Exception("No changes generated by AI")

        return response


    async def perform_diff(self, query: str) -> str:
        try:
            self._check_code_chunks()

            print(f"{Colors.INFO}🔍 Processing query...")

            codebase_stats = self.storage.get_codebase_stats()

            print(f"{Colors.INFO}🤖 Analyzing query scope...")
            scope = await self.scope_analyzer.analyze(query, codebase_stats=codebase_stats)

            effective_top_k = scope.suggested_top_k
            if scope.target_files:
                total_file_chunks = sum(
                    codebase_stats.chunks_by_file.get(f, 0) for f in scope.target_files
                )
                if total_file_chunks > 0:
                    effective_top_k = min(scope.suggested_top_k, total_file_chunks)
            elif codebase_stats.total_chunks > 0:
                effective_top_k = min(scope.suggested_top_k, codebase_stats.total_chunks)

            print(f"{Colors.HEADER}📊 Scope Analysis:")
            print(f"{Colors.INFO}  - Type: {scope.scope_type}")
            print(f"{Colors.INFO}  - Confidence: {scope.confidence:.2f}")
            print(f"{Colors.INFO}  - Intent: {scope.intent_description}")
            if scope.target_files:
                print(f"{Colors.MUTED}  - Target Files: {', '.join(scope.target_files)}")
            if scope.target_functions:
                print(f"{Colors.MUTED}  - Target Functions: {', '.join(scope.target_functions)}")
            print(
                f"{Colors.INFO}  - Effective Chunks: {effective_top_k} (suggested: {scope.suggested_top_k})"
            )

            if scope.confidence < 0.7:
                return f"Confidence is low, skipping diff apply operation: {scope.confidence:.2f}"

            print(f"{Colors.INFO}🔎 Retrieving and reranking code chunks...")

            code_chunks = self.storage.search_code_chunks(
                query,
                top_k=effective_top_k,
                rerank=True,
                target_functions=scope.target_functions,
                target_files=scope.target_files,
            )
            if code_chunks:
                self.storage.send_score_retrieval(code_chunks)

            if scope.target_files:
                target_file_set = set(scope.target_files)
                code_chunks = [
                    chunk for chunk in code_chunks if chunk["filename"] in target_file_set
                ]

            if not code_chunks:
                return "Nothing found. Please try a different query."

            for filename in {chunk["filename"] for chunk in code_chunks}:
                self.storage.store_code_chunks(filename)

            print(f"{Colors.HEADER}📝 Selected {len(code_chunks)} chunk(s) for modification:")

            for i, chunk in enumerate(code_chunks, 1):
                ce_score = chunk.get("cross_encoder_score", 0)
                print(
                    f"{Colors.MUTED}  {i}. {chunk['type']} '{chunk['name']}' in {chunk['filename']} "
                    f"(bi: {chunk['similarity']:.3f}, ce: {ce_score:.3f})"
                )

            context_chunks = self._build_chunk_context(code_chunks)

            chunk_names = {chunk["name"] for chunk in code_chunks}

            response = await self._adjust_instructions(query, scope, context_chunks, len(code_chunks), chunk_names)

            changes: list[CodeChange] = []
            for output in response.output.changes:
                old_code = self._clean_code_response(str(output.old_code))
                new_code = self._clean_code_response(str(output.new_code))
                changes.append(CodeChange(
                    old_code=old_code,
                    new_code=new_code,
                    filename=output.filename,
                    chunk_name=output.chunk_name,
                ))

            print(f"{Colors.INFO}📝 {len(changes)} diff(s) planned...")

            print(f"{Colors.HEADER}{'='*50}")
            print(f"{Colors.HEADER}PROPOSED CHANGES")
            print(f"{Colors.HEADER}{'='*50}")

            approved_changes: list[CodeChange] = []

            for change in changes:
                diff = self._generate_diff(change.old_code, change.new_code, change.filename)

                print(f"{Colors.HEADER}File: {Colors.MUTED}{change.filename}")
                print(f"{Colors.HEADER}Target: {Colors.MUTED}{change.chunk_name}")
                print(f"{Colors.HEADER}Diff:")
                print(_colorize_diff(diff))
                print(f"{Colors.HEADER}{'-'*30}")

                if input(f"{Colors.PROMPT}Apply this change? (y/n): {Colors.RESET}").strip().lower() == "y":
                    approved_changes.append(change)

            if not approved_changes:
                return "No changes applied"

            target_files = {c.filename for c in approved_changes}
            print(f"{Colors.HEADER}{'='*50}")
            print(f"{Colors.INFO}Applying {len(approved_changes)} change(s) to: {Colors.MUTED}{', '.join(target_files)}")
            print(f"{Colors.HEADER}{'='*50}")

            for change in approved_changes:
                self._apply_change(change, target_files)

            return "Diff applied"

        except Exception as e:
            return f"Error in code workflow: {str(e)}"

    def _generate_diff(self, original: str, modified: str, filename: str = "file.py") -> str:
        """Generate a unified diff between original and modified code"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )

        return "".join(diff)

    def get_function_signatures(self, filename: str | None = None) -> str:
        try:
            chunks_metadata_path = os.path.join(self.storage.storage_dir, "chunks_metadata.npy")

            if not os.path.exists(chunks_metadata_path):
                return "No code chunks found. Run /chunks first."

            metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

            if filename:
                metadata = [chunk for chunk in metadata if chunk["filename"] == filename]

            functions = [chunk for chunk in metadata if chunk["type"] == "function"]
            classes = [chunk for chunk in metadata if chunk["type"] == "class"]

            result = f"{Colors.HEADER}Code Structure:\n"

            if functions:
                result += f"\n{Colors.HEADER}Functions:\n"
                for func in functions:
                    result += f"{Colors.MUTED}  - {func['name']} (line {func['lineno']}) in {func['filename']}\n"

            if classes:
                result += f"\n{Colors.HEADER}Classes:\n"
                for cls in classes:
                    result += f"{Colors.MUTED}  - {cls['name']} (line {cls['lineno']}) in {cls['filename']}\n"

            return result

        except Exception as e:
            return f"Error getting function signatures: {str(e)}"

    def _clean_code_response(self, code: str) -> str:
        """Clean AI response to extract just the code"""
        if code.startswith("```python"):
            code = code.split("```python")[1]
        if code.startswith("```"):
            code = code.split("```")[1]
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]
        code = code.lstrip("\n")
        code = code.rstrip("\n")
        return code

    def _apply_change(self, change: CodeChange, target_files: set[str]) -> None:
        """Apply a single search/replace change to a file."""
        try:
            file_path = os.path.join(self.storage.app_dir, change.filename)

            if not change.old_code:
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        content = f.read()
                    content = content.rstrip("\n") + "\n\n\n" + change.new_code + "\n"
                else:
                    content = change.new_code + "\n"
                with open(file_path, "w") as f:
                    f.write(content)
            else:
                with open(file_path, "r") as f:
                    content = f.read()

                if change.old_code not in content:
                    print(f"{Colors.ERROR}old_code not found in {change.filename}, skipping{Colors.RESET}")
                    return

                content = content.replace(change.old_code, change.new_code, 1)
                with open(file_path, "w") as f:
                    f.write(content)

            for target_file in target_files:
                self.storage.store_code_chunks(target_file)
        except Exception as e:
            print(f"{Colors.ERROR}Error applying change: {str(e)}{Colors.RESET}")
