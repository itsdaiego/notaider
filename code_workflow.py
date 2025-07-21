import os
import numpy as np
import difflib

from colors import Colors


class CodeWorkflow:
    def __init__(self, storage, model, client):
        self.storage = storage
        self.model = model
        self.client = client

    def _ensure_chunks_ready(self):
        try:
            chunks_index_path = os.path.join(self.storage.storage_dir, 'chunks_index.faiss')
            if not os.path.exists(chunks_index_path):
                print(f"{Colors.GREEN}Initializing code chunks database...")
                self.storage.store_code_chunks()
                print(f"{Colors.GREEN}Code chunks ready!")
        except Exception as e:
            print(f"{Colors.GREEN}Note: Could not initialize chunks database: {e}")

    async def perform_diff(self, query: str) -> str:
        try:
            self._ensure_chunks_ready()

            print(f"{Colors.GREEN}🔍 Processing query...")
            code_chunks = self.storage.search_code_chunks(query, top_k=5)

            if not code_chunks:
                return "Nohing found. Please try a different query."

            for i, chunk in enumerate(code_chunks, 1):
                print(f"{Colors.GREEN}  {i}. {chunk['type']} '{chunk['name']}' in {chunk['filename']} (similarity: {chunk['similarity']:.3f})")

            best_chunk = code_chunks[0]
            transformation_prompt = f"""
            Here is a {best_chunk['type']} from {best_chunk['filename']}:

            {best_chunk['code']}

            User request: {query}

            Please provide the transformed code that implements the requested change.
            Return only the modified code without explanations.
            """

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": transformation_prompt}]
            )

            updated_code = response.content[0].text

            # remove md code blocks if present
            if updated_code.startswith('```python'):
                updated_code = updated_code.split('```python')[1]
            if updated_code.startswith('```'):
                updated_code = updated_code.split('```')[1]
            if updated_code.endswith('```'):
                updated_code = updated_code.rsplit('```', 1)[0]
            updated_code = updated_code

            print(f"{Colors.GREEN}📝 Generating diff preview...")
            diff = self._generate_diff(
                best_chunk['code'],
                updated_code,
                best_chunk['filename']
            )

            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}PROPOSED CHANGES")
            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}File: {best_chunk['filename']}")
            print(f"{Colors.GREEN}Target: {best_chunk['type']} '{best_chunk['name']}' (lines {best_chunk['lineno']}-{best_chunk['end_lineno']})")
            print(f"{Colors.GREEN}{'='*50}")
            print(f"{Colors.GREEN}Diff:")
            print(diff)
            print(f"{Colors.GREEN}{'='*50}")

            try:
                permission = input("Apply these changes? (y/n): ").strip().lower()

                if permission == 'y' or permission == 'yes':
                    result = self._apply_code_changes(best_chunk, updated_code, diff)
                    return result
                else:
                    return f"{Colors.GREEN}Changes cancelled by user."
            except KeyboardInterrupt:
                return f"{Colors.GREEN}Changes cancelled by user."

        except Exception as e:
            return f"Error in code workflow: {str(e)}"

    def _apply_code_changes(self, chunk: dict, updated_code: str, diff: str) -> str:
        try:
            file_path = os.path.join(self.storage.app_dir, chunk['filename'])
            with open(file_path, 'r') as f:
                full_content = f.read()

            lines = full_content.split('\n')
            start_line = chunk['lineno'] - 1
            end_line = chunk['end_lineno']

            new_lines = lines[:start_line] + updated_code.split('\n') + lines[end_line:]
            new_content = '\n'.join(new_lines)

            with open(file_path, 'w') as f:
                f.write(new_content)

            self.storage.store_code_chunks()

            return f"""
            {Colors.GREEN}✅ Changes applied successfully!

{Colors.GREEN}File: {chunk['filename']}
{Colors.GREEN}Modified: {chunk['type']} '{chunk['name']}'

{Colors.GREEN}Summary:
{diff}
"""

        except Exception as e:
            return f"Error applying changes: {str(e)}"

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
