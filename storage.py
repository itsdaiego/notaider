import ast
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer

load_dotenv()


class Storage:
    def __init__(self, storage_dir="db", app_dir="app"):
        self.storage_dir = storage_dir
        self.app_dir = app_dir
        self._model = None
        self._cross_encoder = None

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

    def _load_index(
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

        index, existing_filenames = self._load_index("index.faiss", "filenames.npy")

        texts = []
        filenames = []

        for path in Path(self.app_dir).rglob(f"*{match}*" if match else "*"):
            if path.is_file() and path.name.endswith(".py"):
                if path.name not in existing_filenames:
                    with open(path, "r", encoding="utf-8") as file:
                        texts.append(file.read())
                        filenames.append(path.name)

        if not texts:
            return existing_filenames, []

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        all_filenames = existing_filenames + filenames
        self._save_index(index, embeddings, "index.faiss", "filenames.npy", all_filenames)

        return all_filenames, filenames

    def search_content(self, query, top_k=5):
        index_path = os.path.join(self.storage_dir, "index.faiss")
        filenames_path = os.path.join(self.storage_dir, "filenames.npy")

        index = faiss.read_index(index_path)
        filenames = np.load(filenames_path).tolist()

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = index.search(query_embedding, top_k)

        results = []

        # converts distance to similarities
        # for example:
        # distance = 4 -> 1 / (1 + 4) = 0.2
        # 0.2 is the similarity score, the higher the distance, the lower will the similarity score be.
        similarities = 1 / (1 + distances[0])

        # zip is used to combine the most similar indices with their matching similarity scores
        # this creates a structure like:
        # indices = [0, 1, 2]
        # similarities = [0.8, 0.6, 0.5]
        # results = [(0, 0.8), (1, 0.6), (2, 0.5)]
        for idx, similarity in zip(indices[0], similarities):
            filename = filenames[idx]
            file_path = os.path.join(self.app_dir, filename)

            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()

                    # increase similarity if filename is mentioned in initial query
                    similarity_boost = self._perform_similarity_boost(filename, query)
                    similarity = min(similarity + similarity_boost, 1.0)  # Cap at 1.0

                    if similarity < 0.5:
                        continue

                    results.append(
                        {"filename": filename, "content": content, "similarity": similarity}
                    )
            except FileNotFoundError:
                print(f"Warning: File {filename} not found in {self.app_dir}")
                continue

        results.sort(key=lambda item: item["similarity"], reverse=True)
        return results

    def _perform_similarity_boost(self, filename, query):
        boost = 0.0
        base_filename = filename.replace(".py", "")
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

        chunks_index, existing_metadata = self._load_index(
            "chunks_index.faiss", "chunks_metadata.npy", allow_pickle=True
        )

        chunks_data = []
        new_chunks = []

        for path in Path(self.app_dir).rglob(f"*{match}*" if match else "*"):
            if path.is_file() and path.name.endswith(".py"):
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()

                    chunks = self._parse_code_chunks(content, str(path))

                    for chunk in chunks:
                        chunk_id = f"{path.name}:{chunk['type']}:{chunk['name']}"

                        if not any(meta["chunk_id"] == chunk_id for meta in existing_metadata):
                            chunks_data.append(chunk["code"])
                            new_chunks.append(
                                {
                                    "chunk_id": chunk_id,
                                    "filename": path.name,
                                    "type": chunk["type"],
                                    "name": chunk["name"],
                                    "lineno": chunk["lineno"],
                                    "end_lineno": chunk["end_lineno"],
                                    "code": chunk["code"],
                                }
                            )

        if not chunks_data:
            return existing_metadata, []

        embeddings = self.model.encode(chunks_data, convert_to_numpy=True)
        all_metadata = existing_metadata + new_chunks
        self._save_index(
            chunks_index, embeddings, "chunks_index.faiss", "chunks_metadata.npy", all_metadata
        )

        return all_metadata, new_chunks

    def _parse_code_chunks(self, code: str, filepath: str) -> Iterator[dict[str, Any]]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
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
            _, files = self._load_index("index.faiss", "filenames.npy")
            print("found files", files)
            return files
        except Exception as e:
            print(f"Error listing indexed files: {e}")
            return []

    def search_code_chunks(
        self, query: str, top_k: int = 5, return_all_scores: bool = False, rerank: bool = False
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[float]]:
        chunks_index_path = os.path.join(self.storage_dir, "chunks_index.faiss")
        chunks_metadata_path = os.path.join(self.storage_dir, "chunks_metadata.npy")

        if not os.path.exists(chunks_index_path) or not os.path.exists(chunks_metadata_path):
            return ([], []) if return_all_scores else []

        chunks_index = faiss.read_index(chunks_index_path)
        metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

        search_k = min(max(top_k * 3, 15), len(metadata))

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = chunks_index.search(query_embedding, search_k)

        results = []
        similarities = 1 / (1 + distances[0])

        for idx, similarity in zip(indices[0], similarities):
            if idx < len(metadata):
                chunk_meta = metadata[idx]

                boost = 0.0
                query_words = set(query.lower().split())
                chunk_name_lower = chunk_meta["name"].lower()

                chunk_name_boost_exact = float(os.getenv("CHUNK_NAME_BOOST_EXACT", "0.8"))
                chunk_name_boost_partial = float(os.getenv("CHUNK_NAME_BOOST_PARTIAL", "0.4"))

                if chunk_name_lower in query_words:
                    boost = chunk_name_boost_exact
                elif chunk_name_lower in query.lower():
                    is_false_positive = any(
                        word != chunk_name_lower and word in chunk_name_lower
                        for word in query_words
                    )
                    if not is_false_positive:
                        boost = chunk_name_boost_partial

                similarity = min(similarity + boost, 1.0)

                results.append(
                    {
                        "chunk_id": chunk_meta["chunk_id"],
                        "filename": chunk_meta["filename"],
                        "type": chunk_meta["type"],
                        "name": chunk_meta["name"],
                        "lineno": chunk_meta["lineno"],
                        "end_lineno": chunk_meta["end_lineno"],
                        "code": chunk_meta["code"],
                        "similarity": similarity,
                    }
                )

        results.sort(key=lambda item: item["similarity"], reverse=True)

        if rerank and results:
            results = self.rerank_results(query, results)

        if return_all_scores:
            score_key = "cross_encoder_score" if rerank else "similarity"
            all_scores = [r.get(score_key, r["similarity"]) for r in results]
            return results[:top_k], all_scores

        return results[:top_k]

    def rerank_results(
        self, query: str, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not results:
            return results

        pairs = [[query, chunk["code"]] for chunk in results]
        scores = self.cross_encoder.predict(pairs)

        for i, chunk in enumerate(results):
            chunk["cross_encoder_score"] = float(scores[i])

        results.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
        return results

    def find_functions_by_name(self, function_name: str) -> list[dict[str, Any]]:
        chunks_metadata_path = os.path.join(self.storage_dir, "chunks_metadata.npy")

        if not os.path.exists(chunks_metadata_path):
            return []

        metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

        matching_functions = []
        for chunk_meta in metadata:
            if chunk_meta["type"] == "function" and chunk_meta["name"] == function_name:
                matching_functions.append(chunk_meta)

        return matching_functions

    def get_codebase_stats(self) -> dict[str, Any]:
        chunks_metadata_path = os.path.join(self.storage_dir, "chunks_metadata.npy")

        if not os.path.exists(chunks_metadata_path):
            return {
                "total_chunks": 0,
                "chunks_by_file": {},
                "chunks_by_type": {"function": 0, "class": 0},
            }

        metadata: list[dict[str, Any]] = np.load(chunks_metadata_path, allow_pickle=True).tolist()

        chunks_by_file: dict[str, int] = {}
        chunks_by_type: dict[str, int] = {"function": 0, "class": 0}

        for chunk in metadata:
            filename = chunk["filename"]
            chunk_type = chunk["type"]
            chunks_by_file[filename] = chunks_by_file.get(filename, 0) + 1
            if chunk_type in chunks_by_type:
                chunks_by_type[chunk_type] += 1

        return {
            "total_chunks": len(metadata),
            "chunks_by_file": chunks_by_file,
            "chunks_by_type": chunks_by_type,
        }
