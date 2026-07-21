import ast
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import TypedDict, cast

import faiss
from langfuse import get_client
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer

from utils import distance_to_similarity


class ParsedCodeChunk(TypedDict):
    type: str
    name: str
    lineno: int
    end_lineno: int
    code: str
    filepath: str


class CodeChunk(TypedDict):
    chunk_id: str
    filename: str
    type: str
    name: str
    lineno: int
    end_lineno: int
    code: str


class SearchedCodeChunk(CodeChunk, total=False):
    similarity: float
    cross_encoder_score: float


@dataclass
class CodebaseStats:
    total_chunks: int
    chunks_by_file: dict[str, int]
    chunks_by_type: dict[str, int]


@dataclass
class SearchResult:
    filename: str
    content: str
    similarity: float

load_dotenv()


class Storage:
    def __init__(self, storage_dir="db", app_dir="app", model=None, cross_encoder=None):
        self.storage_dir = storage_dir
        self.app_dir = app_dir
        self._model = model
        self._cross_encoder = cross_encoder

    @property
    def model(self):
        if self._model is None:
            embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self._model = SentenceTransformer(embedding_model)
        return self._model

    @property
    def cross_encoder(self):
        if self._cross_encoder is None:
            cross_encoder_model = os.getenv(
                "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
            self._cross_encoder = CrossEncoder(cross_encoder_model)
        return self._cross_encoder

    def _ensure_dirs(self):
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.app_dir, exist_ok=True)

    def load_index(
        self, index_filename: str, metadata_filename: str, allow_pickle: bool = False
    ) -> tuple:
        index_path = os.path.join(self.storage_dir, index_filename)
        metadata_path = os.path.join(self.storage_dir, metadata_filename)

        if os.path.exists(index_path) and os.path.exists(metadata_path):
            index = faiss.read_index(index_path)
            data = np.load(metadata_path, allow_pickle=allow_pickle).tolist()
            return index, data

        return None, []

    def _save_index(
        self, index, embeddings, index_filename: str, metadata_filename: str, all_metadata: list
    ):
        if index is None:
            index = faiss.IndexFlatL2(embeddings.shape[1])

        index.add(embeddings)

        faiss.write_index(index, os.path.join(self.storage_dir, index_filename))
        np.save(os.path.join(self.storage_dir, metadata_filename), all_metadata)

    def ensure_storage_dir(self):
        os.makedirs(self.storage_dir, exist_ok=True)

    def store_files(self, match: str = ""):
        self._ensure_dirs()

        index, existing_filenames = self.load_index("filenames_index.faiss", "filenames.npy")

        texts = []
        filenames = []

        for path in Path(self.app_dir).rglob("*.py"):
            if path.is_file() and (not match or match in str(path)):
                if path.name not in existing_filenames:
                    with open(path, "r", encoding="utf-8") as file:
                        texts.append(file.read())
                        filenames.append(path.name)

        if not texts:
            return existing_filenames, []

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        all_filenames = existing_filenames + filenames
        self._save_index(index, embeddings, "filenames_index.faiss", "filenames.npy", all_filenames)

        return all_filenames, filenames

    def search_content(self, query, top_k=5) -> list[SearchResult]:
        self._ensure_dirs()

        index_path = os.path.join(self.storage_dir, "filenames_index.faiss")
        filenames_path = os.path.join(self.storage_dir, "filenames.npy")

        index = faiss.read_index(index_path)
        filenames = np.load(filenames_path).tolist()

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = index.search(query_embedding, top_k)

        results: list[SearchResult] = []

        similarities = distance_to_similarity(distances[0])

        for idx, similarity in zip(indices[0], similarities):
            filename = filenames[idx]
            file_path = os.path.join(self.app_dir, filename)

            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()

                    similarity_boost = self._perform_similarity_boost(filename, query)
                    similarity = min(similarity + similarity_boost, 1.0)

                    if similarity < 0.5:
                        continue

                    results.append(SearchResult(filename=filename, content=content, similarity=similarity))
            except FileNotFoundError:
                print(f"Warning: File {filename} not found in {self.app_dir}")
                continue
            except Exception as e:
                print(f"Something went wrong: {e}")
                continue

        results.sort(key=lambda item: item.similarity, reverse=True)
        return results

    def _perform_similarity_boost(self, filename, query):
        boost = 0.0
        file_type = filename[:len(filename) - 3]
        base_filename = filename.replace(f"{file_type}", "")
        query_lower = query.lower()

        filename_boost_exact = float(os.getenv("FILENAME_BOOST_EXACT", "0.3"))
        filename_boost_normalized = float(os.getenv("FILENAME_BOOST_NORMALIZED", "0.25"))

        if base_filename.lower() in query_lower:
            boost = max(boost, filename_boost_exact)

        normalized_filename = re.sub(r"[_-]", " ", base_filename.lower())
        if normalized_filename in query_lower:
            boost = max(boost, filename_boost_normalized)

        return boost

    def store_code_chunks(self, match: str = ""):
        self._ensure_dirs()

        chunks_index, existing_metadata = self.load_index(
            "chunks_index.faiss", "chunks_metadata.npy", allow_pickle=True
        )

        existing_by_id = {
            meta["chunk_id"]: (position, meta) for position, meta in enumerate(existing_metadata)
        }
        stale_ids = set()

        changed_chunks_data = []
        changed_metadata = []

        for path in Path(self.app_dir).rglob("*.py"):
            if path.is_file() and (not match or match in str(path)):
                relative_path = str(path.relative_to(self.app_dir))
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()

                for chunk in self._parse_code_chunks(content, str(path)):
                    chunk_id = f"{relative_path}:{chunk['type']}:{chunk['name']}"
                    existing = existing_by_id.get(chunk_id)

                    if existing and existing[1]["code"] == chunk["code"]:
                        continue

                    if existing:
                        stale_ids.add(chunk_id)

                    changed_chunks_data.append(chunk["code"])
                    changed_metadata.append(
                        {
                            "chunk_id": chunk_id,
                            "filename": relative_path,
                            "type": chunk["type"],
                            "name": chunk["name"],
                            "lineno": chunk["lineno"],
                            "end_lineno": chunk["end_lineno"],
                            "code": chunk["code"],
                        }
                    )

        if not changed_chunks_data:
            return existing_metadata, []

        unchanged_metadata = []
        unchanged_embeddings = []
        for position, meta in enumerate(existing_metadata):
            if meta["chunk_id"] in stale_ids:
                continue

            unchanged_metadata.append(meta)
            unchanged_embeddings.append(chunks_index.reconstruct(position))

        changed_embeddings = self.model.encode(changed_chunks_data, convert_to_numpy=True)
        all_metadata = unchanged_metadata + changed_metadata
        all_embeddings = (
            np.vstack([np.array(unchanged_embeddings), changed_embeddings])
            if unchanged_embeddings
            else changed_embeddings
        )

        fresh_index = faiss.IndexFlatL2(changed_embeddings.shape[1])
        self._save_index(
            fresh_index, all_embeddings, "chunks_index.faiss", "chunks_metadata.npy", all_metadata
        )

        return all_metadata, changed_metadata

    def _parse_code_chunks(self, code: str, filepath: str) -> Iterator[ParsedCodeChunk]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
            line_count = code.count("\n") + 1
            yield {
                "type": "module",
                "name": Path(filepath).stem,
                "lineno": 1,
                "end_lineno": line_count,
                "code": code,
                "filepath": filepath,
            }
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                end_lineno = getattr(node, "end_lineno", node.lineno)
                yield {
                    "type": "function" if isinstance(node, ast.FunctionDef) else "class",
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": end_lineno,
                    "code": self._extract_code_segment(code, node.lineno, end_lineno),
                    "filepath": filepath,
                }

    def _extract_code_segment(self, code: str, start_line: int, end_line: int) -> str:
        lines = code.split("\n")
        return "\n".join(lines[start_line - 1 : end_line])

    def list_indexed_files(self) -> list[str]:
        try:
            print("starting lookup")
            _, files = self.load_index("filenames_index.faiss", "filenames.npy")
            print("found files", files)
            return files
        except Exception as e:
            print(f"Error listing indexed files: {e}")
            return []

    def search_code_chunks(
        self,
        query: str,
        top_k: int = 5,
        rerank: bool = False,
        target_functions: list[str] | None = None,
        target_files: list[str] | None = None,
    ) -> list[SearchedCodeChunk]:
        self._ensure_dirs()

        (chunks_index, metadata) = self.load_index("chunks_index.faiss", "chunks_metadata.npy", True)
        metadata = cast(list[CodeChunk], metadata)

        if chunks_index is None or not metadata:
            return []

        search_k = min(max(top_k * 3, 15), len(metadata))

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = chunks_index.search(query_embedding, search_k)

        results: list[SearchedCodeChunk] = []
        similarities = distance_to_similarity(distances[0])

        # since we have one query, indices is always 0
        for idx, similarity in zip(indices[0], similarities):
            if idx < len(metadata):
                chunk: SearchedCodeChunk = {**metadata[idx], "similarity": float(similarity)}  # type: ignore[misc]
                results.append(chunk)

        if target_files:
            retrieved_files = {chunk["filename"] for chunk in results}
            missing_files = set(target_files) - retrieved_files
            if missing_files:
                for chunk_meta in metadata:
                    if chunk_meta["filename"] in missing_files:
                        injected: SearchedCodeChunk = {**chunk_meta, "similarity": 0.0}  # type: ignore[misc]
                        results.append(injected)

        if rerank and results:
            results = self.rerank_results(query, results, target_functions or [], target_files)

        return results[:top_k]

    def rerank_results(
        self,
        query: str,
        results: list[SearchedCodeChunk],
        target_functions: list[str],
        target_files: list[str] | None = None,
    ) -> list[SearchedCodeChunk]:
        if not results:
            return results

        pairs = [[query, chunk["code"]] for chunk in results]
        scores = self.cross_encoder.predict(pairs)

        target_set = set(target_functions)
        target_file_set = set(target_files) if target_files else set()
        for i, chunk in enumerate(results):
            score = float(scores[i])
            if chunk["name"] in target_set:
                score += 10.0
            if chunk["filename"] in target_file_set:
                score += 5.0
            chunk["cross_encoder_score"] = score

        results.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
        return results

    def send_score_retrieval(self, results: list[SearchedCodeChunk]) -> None:
        try:
            langfuse = get_client()
            score = results[0]["cross_encoder_score"]
            normalized = distance_to_similarity(np.exp(-score))
            langfuse.score_current_span(
                name="retrieval_relevance",
                value=float(normalized),
                data_type="NUMERIC",
            )
        except Exception:
            pass

    def format_search_results(self, query: str, top_k: int = 5) -> str:
        """Format code chunk search results as a readable string for LLM consumption."""
        results = self.search_code_chunks(query, top_k=top_k, rerank=True)
        if not results:
            return "No results found."
        self.send_score_retrieval(results)
        output = ""
        for i, chunk in enumerate(results, 1):
            output += f"\n{i}: {chunk['filename']} - {chunk['type']} '{chunk['name']}' (line {chunk['lineno']}):\n"
            output += f"```\n{chunk['code']}\n```\n"
        return output

    def run_command(self, command: str) -> str:
        """Run a shell command scoped to app_dir, return stdout+stderr (max 5000 chars)."""
        try:
            result = subprocess.run(
                command, shell=True, cwd=self.app_dir,
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout + result.stderr
            return output[:5000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out (10s limit)."
        except Exception as e:
            return f"Error: {e}"

    def find_functions_by_name(self, function_name: str) -> list[CodeChunk]:
        chunks_metadata_path = os.path.join(self.storage_dir, "chunks_metadata.npy")

        if not os.path.exists(chunks_metadata_path):
            return []

        metadata = cast(list[CodeChunk], np.load(chunks_metadata_path, allow_pickle=True).tolist())

        matching_functions = []
        for chunk_meta in metadata:
            if chunk_meta["type"] == "function" and chunk_meta["name"] == function_name:
                matching_functions.append(chunk_meta)

        return matching_functions

    def get_codebase_stats(self) -> CodebaseStats:
        chunks_metadata_path = os.path.join(self.storage_dir, "chunks_metadata.npy")

        if not os.path.exists(chunks_metadata_path):
            return CodebaseStats(
                total_chunks=0,
                chunks_by_file={},
                chunks_by_type={"function": 0, "class": 0},
            )

        metadata = cast(list[CodeChunk], np.load(chunks_metadata_path, allow_pickle=True).tolist())

        chunks_by_file: dict[str, int] = {}
        chunks_by_type: dict[str, int] = {"function": 0, "class": 0}

        for chunk in metadata:
            filename = chunk["filename"]
            chunk_type = chunk["type"]
            chunks_by_file[filename] = chunks_by_file.get(filename, 0) + 1
            if chunk_type in chunks_by_type:
                chunks_by_type[chunk_type] += 1

        return CodebaseStats(
            total_chunks=len(metadata),
            chunks_by_file=chunks_by_file,
            chunks_by_type=chunks_by_type,
        )
