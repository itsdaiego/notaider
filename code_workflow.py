import difflib
import os

import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent

from colors import Colors
from scope_analyzer import ScopeAnalyzer

load_dotenv()


class CodeWorkflowOutput(BaseModel):
    code: str
    filename: str
    chunk_name: str


class CodeWorkflow:
    def __init__(self, storage, model, client):
        self.storage = storage
        self.model = model
        self.client = client
        self.scope_analyzer = ScopeAnalyzer()

    def _check_code_chunks(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, "chunks_index.faiss")
            if not os.path.exists(chunks_index_path):
                print(f"{Colors.GREEN}Initializing code chunks database...")
                self.storage.store_code_chunks()
                print(f"{Colors.GREEN}Code chunks ready!")
        except Exception as e:
            print(f"{Colors.GREEN}Note: Could not initialize chunks database: {e}")

    async def perform_diff(self, query: str) -> str:
        try:
            self._check_code_chunks()

            print(f"{Colors.GREEN}🔍 Processing query...")

            codebase_stats = self.storage.get_codebase_stats()

            print(f"{Colors.GREEN}🤖 Analyzing query scope...")
            scope = await self.scope_analyzer.analyze(query, codebase_stats=codebase_stats)

            effective_top_k = scope.suggested_top_k
            if scope.target_file and scope.target_file in codebase_stats["chunks_by_file"]:
                file_chunk_count = codebase_stats["chunks_by_file"][scope.target_file]
                effective_top_k = min(scope.suggested_top_k, file_chunk_count)
            elif codebase_stats["total_chunks"] > 0:
                effective_top_k = min(scope.suggested_top_k, codebase_stats["total_chunks"])

            print(f"{Colors.GREEN}📊 Scope Analysis:")
            print(f"{Colors.GREEN}  - Type: {scope.scope_type}")
            print(f"{Colors.GREEN}  - Confidence: {scope.confidence:.2f}")
            print(f"{Colors.GREEN}  - Intent: {scope.intent_description}")
            if scope.target_file:
                print(f"{Colors.GREEN}  - Target File: {scope.target_file}")
            if scope.target_functions:
                print(f"{Colors.GREEN}  - Target Functions: {', '.join(scope.target_functions)}")
            print(
                f"{Colors.GREEN}  - Effective Chunks: {effective_top_k} (suggested: {scope.suggested_top_k})"
            )

            print(f"{Colors.GREEN}🔎 Retrieving and reranking code chunks...")
            code_chunks = self.storage.search_code_chunks(query, top_k=effective_top_k, rerank=True)

            if scope.target_file:
                code_chunks = [
                    chunk for chunk in code_chunks if chunk["filename"] == scope.target_file
                ]

            if not code_chunks:
                return "Nothing found. Please try a different query."

            print(f"{Colors.GREEN}📝 Selected {len(code_chunks)} chunk(s) for modification:")
            for i, chunk in enumerate(code_chunks, 1):
                ce_score = chunk.get("cross_encoder_score", 0)
                print(
                    f"{Colors.GREEN}  {i}. {chunk['type']} '{chunk['name']}' in {chunk['filename']} "
                    f"(bi: {chunk['similarity']:.3f}, ce: {ce_score:.3f})"
                )

            changes = []

            # Build detailed chunk context with rankings
            chunk_context = []
            for i, c in enumerate(code_chunks, 1):
                ce_score = c.get("cross_encoder_score", 0)
                chunk_context.append(
                    f"Chunk #{i} (relevance: {ce_score:.3f}, HIGHEST MATCH)"
                    if i == 1
                    else f"Chunk #{i} (relevance: {ce_score:.3f})"
                )
                chunk_context.append(f"  - Type: {c['type']}")
                chunk_context.append(f"  - Name: {c['name']}")
                chunk_context.append(f"  - File: {c['filename']}")

                # Calculate indentation level for emphasis
                code_lines = c["code"].split("\n")
                first_line = code_lines[0] if code_lines else ""
                indent_spaces = len(first_line) - len(first_line.lstrip(" "))

                chunk_context.append(
                    f"  - Indentation: {indent_spaces} spaces (MUST BE PRESERVED EXACTLY)"
                )
                chunk_context.append(f"  - Code:\n{c['code']}")
                chunk_context.append("")

            # Adjust instructions based on scope
            if scope.scope_type in ["file", "project", "all"]:
                scope_instruction = f"""
            SCOPE: The user wants to modify {scope.intent_description}.
            This is a BROAD scope ({scope.scope_type}) - you MUST return modifications for ALL {len(code_chunks)} chunks provided below.
            Each chunk should receive the modification requested by the user.
            """
            elif scope.scope_type == "multiple":
                scope_instruction = f"""
            SCOPE: The user wants to modify {scope.intent_description}.
            This is a MULTIPLE scope - modify the chunks that best match the user's specific targets.
            Target functions/classes: {', '.join(scope.target_functions) if scope.target_functions else 'infer from query'}
            You should return modifications for MULTIPLE chunks (not just one).
            """
            else:
                scope_instruction = f"""
            SCOPE: The user wants to modify {scope.intent_description}.
            This is a SINGLE scope - only modify the chunk that best matches the user's request (typically Chunk #1).
            """

            transformation_prompt = f"""
            Here are the code chunks ranked by relevance to the user's request.

            {chr(10).join(chunk_context)}

            User request: {query}

            {scope_instruction}

            CRITICAL INSTRUCTIONS:
            1. Read the SCOPE section above carefully to understand how many chunks to modify
            2. If modifying multiple chunks, return one CodeWorkflowOutput entry for EACH chunk
            3. If modifying a single chunk, return only ONE CodeWorkflowOutput entry

            For EACH chunk that needs modification, return a CodeWorkflowOutput with:
            - code: the transformed code for that specific chunk
            - filename: the filename of that chunk (e.g., "todo.py")
            - chunk_name: the name of the function/class being modified (e.g., "get_todo", "TodoItem")

            CRITICAL INDENTATION RULES (FAILURE TO FOLLOW WILL BREAK THE CODE):
            1. Count the leading spaces in the FIRST line of the original code - this is the BASE indentation
            2. Your output MUST start with EXACTLY the same number of leading spaces
            3. Every line in your output must maintain the EXACT same indentation structure as the original
            4. DO NOT strip, reduce, or modify any leading whitespace
            5. If the original first line has N spaces, your first line MUST have N spaces
            6. Example: If original starts with "    def" (4 spaces), your output MUST start with "    def" (4 spaces)

            WHAT TO MODIFY:
            - Add/remove/modify the code logic as requested
            - Keep all indentation exactly as it appears in the original

            IMPORTANT: If the user request only targets one specific function/class, only return ONE entry for that function/class.
            """

            # Create a temporary agent with structured output for this specific
            ai_model = os.getenv("AI_MODEL", "gpt-4o-mini")
            structured_agent = Agent(ai_model, output_type=list[CodeWorkflowOutput], retries=5)
            try:
                response = await structured_agent.run(transformation_prompt)
            except ValidationError as ve:
                return f"Error in AI response validation: {ve}"
            except Exception as e:
                return f"Error in AI response: {e}"

            if not response.output:
                return "No changes generated by AI"

            # Filter changes if filename is mentioned in query
            for output in response.output:
                cleaned_code = self._clean_code_response(str(output.code))

                for chunk in code_chunks:
                    if chunk["filename"] == output.filename:
                        # Ensure indentation is preserved
                        # TODO: already handling at the prompt phase
                        # cleaned_code = self._fix_indentation(cleaned_code, chunk['code'])

                        changes.append({"chunk": chunk, "updated_code": cleaned_code})
                        break

            # Generate combined diff
            print(f"{Colors.GREEN}📝 Generating diff preview...")

            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}PROPOSED CHANGES")
            print(f"{Colors.GREEN}{'='*50}")

            target_files = set()

            for change in changes:
                chunk = change["chunk"]
                updated_code = change["updated_code"]
                target_files.add(chunk["filename"])

                diff = self._generate_diff(chunk["code"], updated_code, chunk["filename"])

                print(f"{Colors.GREEN}File: {chunk['filename']}")
                print(
                    f"{Colors.GREEN}Target: {chunk['type']} '{chunk['name']}' (lines {chunk['lineno']}-{chunk['end_lineno']})"
                )
                print(f"{Colors.GREEN}Diff:")
                print(diff)
                print(f"{Colors.GREEN}{'-'*30}")

                if input("Apply this change? (y/n): ").strip().lower() != "y":
                    continue

                print(f"{Colors.GREEN}{'='*50}")
                print(f"{Colors.GREEN}Files to be modified: {', '.join(target_files)}")
                print(f"{Colors.GREEN}{'='*50}")

                self._apply_change(change)

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

            result = f"{Colors.GREEN}Code Structure:\n"

            if functions:
                result += f"\n{Colors.GREEN}Functions:\n"
                for func in functions:
                    result += f"{Colors.GREEN}  - {func['name']} (line {func['lineno']}) in {func['filename']}\n"

            if classes:
                result += f"\n{Colors.GREEN}Classes:\n"
                for cls in classes:
                    result += f"{Colors.GREEN}  - {cls['name']} (line {cls['lineno']}) in {cls['filename']}\n"

            return result

        except Exception as e:
            return f"Error getting function signatures: {str(e)}"

    def _infer_filename_from_query(self, query: str) -> str:
        """Infer target filename from the query text"""
        import re

        # Look for explicit filename mentions
        filename_patterns = [
            r"in\s+(\w+\.py)",  # "in main.py"
            r"(\w+\.py)",  # "main.py"
            r"(\w+)\s+file",  # "main file"
            r"(\w+)\s+module",  # "storage module"
        ]

        for pattern in filename_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                filename = match.group(1)
                if not filename.endswith(".py"):
                    filename += ".py"
                return filename

        return None

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

    def _fix_indentation(self, generated_code: str, original_code: str) -> str:
        """
        Fix indentation of generated code to match original code's base indentation.

        If the AI stripped the leading indentation, this will restore it.
        """
        if not generated_code or not original_code:
            return generated_code

        # Get the base indentation from the original code's first line
        original_lines = original_code.split("\n")
        generated_lines = generated_code.split("\n")

        if not original_lines or not generated_lines:
            return generated_code

        original_first_line = original_lines[0]
        generated_first_line = generated_lines[0]

        # Count leading spaces in original
        original_indent = len(original_first_line) - len(original_first_line.lstrip(" "))
        # Count leading spaces in generated
        generated_indent = len(generated_first_line) - len(generated_first_line.lstrip(" "))

        # If indentation matches, no fix needed
        if original_indent == generated_indent:
            return generated_code

        # Calculate the difference
        indent_diff = original_indent - generated_indent

        # Apply the indentation fix to all lines
        fixed_lines = []
        for line in generated_lines:
            if line.strip():  # Only fix non-empty lines
                if indent_diff > 0:
                    # Add missing indentation
                    fixed_lines.append(" " * indent_diff + line)
                else:
                    # Remove extra indentation (be careful not to remove too much)
                    spaces_to_remove = abs(indent_diff)
                    if line.startswith(" " * spaces_to_remove):
                        fixed_lines.append(line[spaces_to_remove:])
                    else:
                        fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _apply_change(self, change: dict) -> str:
        """Apply a single change to a file"""
        try:
            chunk = change["chunk"]
            updated_code = change["updated_code"]

            file_path = os.path.join(self.storage.app_dir, chunk["filename"])
            with open(file_path, "r") as f:
                full_content = f.read()

            lines = full_content.split("\n")
            start_line = chunk["lineno"] - 1
            end_line = chunk["end_lineno"]

            new_code_lines = updated_code.split("\n")
            modified_lines = lines[:start_line] + new_code_lines + lines[end_line:]

            new_content = "\n".join(modified_lines)
            with open(file_path, "w") as f:
                f.write(new_content)

            self.storage.store_code_chunks()

        except Exception as e:
            return f"Error applying change: {str(e)}"
