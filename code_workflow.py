import os
import numpy as np
import difflib

from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent

from colors import Colors


class CodeWorkflowOutput(BaseModel):
    code: str
    filename: str

class CodeWorkflow:
    def __init__(self, storage, model, client):
        self.storage = storage
        self.model = model
        self.client = client

    def _check_code_chunks(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, 'chunks_index.faiss')
            if not os.path.exists(chunks_index_path):
                print(f"{Colors.GREEN}Initializing code chunks database...")
                self.storage.store_code_chunks()
                print(f"{Colors.GREEN}Code chunks ready!")
        except Exception as e:
            print(f"{Colors.GREEN}Note: Could not initialize chunks database: {e}")

    async def perform_diff(self, query: str, target_filename: str | None = None) -> str:
        try:
            self._check_code_chunks()

            print(f"{Colors.GREEN}🔍 Processing query...")

            if not target_filename:
                target_filename = self._infer_filename_from_query(query)

            code_chunks = self.storage.search_code_chunks(query, top_k=3)

            if not code_chunks:
                return "Nothing found. Please try a different query."

            print(f"{Colors.GREEN}📝 Selected {len(code_chunks)} chunk(s) for modification:")
            for i, chunk in enumerate(code_chunks, 1):
                print(f"{Colors.GREEN}  {i}. {chunk['type']} '{chunk['name']}' in {chunk['filename']} (similarity: {chunk['similarity']:.3f})")

            # Process all selected chunks
            changes = []

            transformation_prompt = f"""
            Here are the relevant chunks for context:
                {', '.join([f"chunk type: {c['type']} ' chunk code: {c['code']}' from filename {c['filename']}" for c in code_chunks])}


            User request: {query}

            CRITICAL: You MUST preserve the EXACT indentation from the original code above.
            - The first line starts with exactly the same whitespace/indentation as shown
            - All subsequent lines must maintain the same relative indentation structure
            - Do NOT change the base indentation level of the code block

            Please provide the transformed code that implements the requested change.
            Return only the modified code without explanations.
            """

            # Create a temporary agent with structured output for this specific 
            structured_agent = Agent('claude-3-5-haiku-20241022', output_type=list[CodeWorkflowOutput], retries=5)
            try:
                response = await structured_agent.run(transformation_prompt)
            except ValidationError as ve:
                return f"Error in AI response validation: {ve}"
            except Exception as e:
                return f"Error in AI response: {e}"

            updated_code = str(response.output[0].code) if response.output else ""

            # remove md code blocks if present
            updated_code = self._clean_code_response(updated_code)

            for chunk in code_chunks:
                changes.append({
                    'chunk': chunk,
                    'updated_code': updated_code
                })

            # Generate combined diff
            print(f"{Colors.GREEN}📝 Generating diff preview...")

            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}PROPOSED CHANGES")
            print(f"{Colors.GREEN}{'='*50}")

            total_diff = ""
            target_files = set()

            for change in changes:
                chunk = change['chunk']
                updated_code = change['updated_code']
                target_files.add(chunk['filename'])

                diff = self._generate_diff(
                    chunk['code'],
                    updated_code,
                    chunk['filename']
                )

                print(f"{Colors.GREEN}File: {chunk['filename']}")
                print(f"{Colors.GREEN}Target: {chunk['type']} '{chunk['name']}' (lines {chunk['lineno']}-{chunk['end_lineno']})")
                print(f"{Colors.GREEN}Diff:")
                print(diff)
                print(f"{Colors.GREEN}{'-'*30}")

                total_diff += f"\n{chunk['filename']} - {chunk['type']} '{chunk['name']}':\n{diff}\n"

            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}Files to be modified: {', '.join(target_files)}")
            print(f"{Colors.GREEN}{'='*50}")

            result = self._apply_multiple_changes(changes)
            return result

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
            lineterm=""
        )

        return ''.join(diff)

    def get_function_signatures(self, filename: str | None = None) -> str:
        try:
            chunks_metadata_path = os.path.join(self.storage.storage_dir, 'chunks_metadata.npy')

            if not os.path.exists(chunks_metadata_path):
                return "No code chunks found. Run /chunks first."

            metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

            if filename:
                metadata = [chunk for chunk in metadata if chunk['filename'] == filename]

            functions = [chunk for chunk in metadata if chunk['type'] == 'function']
            classes = [chunk for chunk in metadata if chunk['type'] == 'class']

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
            r'in\s+(\w+\.py)',  # "in main.py"
            r'(\w+\.py)',       # "main.py"
            r'(\w+)\s+file',    # "main file"
            r'(\w+)\s+module',  # "storage module"
        ]

        for pattern in filename_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                filename = match.group(1)
                if not filename.endswith('.py'):
                    filename += '.py'
                return filename

        return None

    def _clean_code_response(self, code: str) -> str:
        """Clean AI response to extract just the code"""
        if code.startswith('```python'):
            code = code.split('```python')[1]
        if code.startswith('```'):
            code = code.split('```')[1]
        if code.endswith('```'):
            code = code.rsplit('```', 1)[0]
        code = code.lstrip('\n')
        code = code.rstrip('\n')
        return code

    def _apply_multiple_changes(self, changes: list) -> str:
        """Apply multiple changes to files"""
        try:
            changes_by_file = {}
            for change in changes:
                filename = change['chunk']['filename']
                if filename not in changes_by_file:
                    changes_by_file[filename] = []
                changes_by_file[filename].append(change)

            results = []

            for filename, file_changes in changes_by_file.items():
                file_changes.sort(key=lambda x: x['chunk']['lineno'], reverse=True)

                file_path = os.path.join(self.storage.app_dir, filename)
                with open(file_path, 'r') as f:
                    full_content = f.read()

                lines = full_content.split('\n')
                modified_lines = lines.copy()

                for change in file_changes:
                    chunk = change['chunk']
                    updated_code = change['updated_code']

                    start_line = chunk['lineno'] - 1
                    end_line = chunk['end_lineno']

                    new_code_lines = updated_code.split('\n')
                    modified_lines = modified_lines[:start_line] + new_code_lines + modified_lines[end_line:]

                new_content = '\n'.join(modified_lines)
                with open(file_path, 'w') as f:
                    f.write(new_content)

                results.append(f"✅ Modified {len(file_changes)} chunk(s) in {filename}")

            self.storage.store_code_chunks()

            summary = '\n'.join(results)
            return f"""
{Colors.GREEN}✅ All changes applied successfully!

{Colors.GREEN}{summary}

{Colors.GREEN}📁 Files modified: {', '.join(changes_by_file.keys())}
"""

        except Exception as e:
            return f"Error applying multiple changes: {str(e)}"
