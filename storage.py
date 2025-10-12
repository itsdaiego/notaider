import os
import re
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import ast
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Storage():
    def __init__(self, storage_dir='db', app_dir='app'):
        self.storage_dir = storage_dir
        self.app_dir = app_dir
        self._model = None

    @property
    def model(self):
        if self._model is None:
            embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self._model = SentenceTransformer(embedding_model)
        return self._model

    def ensure_storage_dir(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def clean_embeddings(self):
        files_to_remove = ['index.faiss', 'filenames.npy']

        for file in files_to_remove:
            file_path = os.path.join(self.storage_dir, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed: {file_path}")

        print("Database reset complete!")

    def store_files(self, match: str = ""):
        if not os.path.exists(os.path.join(self.storage_dir)):
            os.makedirs(self.storage_dir)

        if not os.path.exists(os.path.join(self.app_dir)):
            os.makedirs(self.app_dir)

        index_path = os.path.join(self.storage_dir, 'index.faiss')
        filenames_path = os.path.join(self.storage_dir, 'filenames.npy')

        if os.path.exists(index_path) and os.path.exists(filenames_path):
            index = faiss.read_index(index_path)
            existing_filenames = np.load(filenames_path).tolist()
        else:
            index = None
            existing_filenames = []

        texts = []
        filenames = []

        for path in Path(self.app_dir).rglob(f"*{match}*" if match else "*"):
            if path.is_file() and path.name.endswith('.py'):
                if path.name not in existing_filenames:
                    with open(path, 'r', encoding='utf-8') as file:
                        texts.append(file.read())
                        filenames.append(path.name)

        if not texts:
            return existing_filenames, []

        embeddings = self.model.encode(texts, convert_to_numpy=True)

        dim = embeddings.shape[1]

        if index is None:
            index = faiss.IndexFlatL2(dim)

        index.add(embeddings)

        all_filenames = existing_filenames + filenames

        faiss.write_index(index, index_path)
        np.save(filenames_path, all_filenames)

        return all_filenames, filenames

    def search_content(self, query, top_k=5):
        index_path = os.path.join(self.storage_dir, 'index.faiss')
        filenames_path = os.path.join(self.storage_dir, 'filenames.npy')

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
                with open(file_path, 'r') as f:
                    content = f.read().strip()

                    # increase similarity if filename is mentioned in initial query
                    similarity_boost = self._perform_similarity_boost(filename, query)
                    similarity = min(similarity + similarity_boost, 1.0)  # Cap at 1.0

                    results.append({
                        'filename': filename,
                        'content': content,
                        'similarity': similarity
                    })
            except FileNotFoundError:
                print(f"Warning: File {filename} not found in {self.app_dir}")
                continue

        results.sort(key=lambda item: item['similarity'], reverse=True)
        return results

    def _perform_similarity_boost(self, filename, query):
        boost = 0.0
        base_filename = filename.replace('.py', '')
        query_lower = query.lower()

        filename_boost_exact = float(os.getenv("FILENAME_BOOST_EXACT", "0.3"))
        filename_boost_normalized = float(os.getenv("FILENAME_BOOST_NORMALIZED", "0.25"))

        if base_filename.lower() in query_lower:
            boost = max(boost, filename_boost_exact)

        normalized_filename = re.sub(r'[_-]', ' ', base_filename.lower())
        if normalized_filename in query_lower:
            boost = max(boost, filename_boost_normalized)

        return boost

    def store_code_chunks(self, match: str = ""):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)

        chunks_index_path = os.path.join(self.storage_dir, 'chunks_index.faiss')
        chunks_metadata_path = os.path.join(self.storage_dir, 'chunks_metadata.npy')

        if os.path.exists(chunks_index_path) and os.path.exists(chunks_metadata_path):
            chunks_index = faiss.read_index(chunks_index_path)
            existing_metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()
        else:
            chunks_index = None
            existing_metadata = []

        chunks_data = []
        new_chunks = []

        for path in Path(self.app_dir).rglob(f"*{match}*" if match else "*"):
            if path.is_file() and path.name.endswith('.py'):
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()

                    chunks = self._parse_code_chunks(content, str(path))

                    for chunk in chunks:
                        chunk_id = f"{path.name}:{chunk['type']}:{chunk['name']}"

                        if not any(meta['chunk_id'] == chunk_id for meta in existing_metadata):
                            chunks_data.append(chunk['code'])
                            new_chunks.append({
                                'chunk_id': chunk_id,
                                'filename': path.name,
                                'type': chunk['type'],
                                'name': chunk['name'],
                                'lineno': chunk['lineno'],
                                'end_lineno': chunk['end_lineno'],
                                'code': chunk['code']
                            })

        if not chunks_data:
            return existing_metadata, []

        embeddings = self.model.encode(chunks_data, convert_to_numpy=True)
        dim = embeddings.shape[1]

        if chunks_index is None:
            chunks_index = faiss.IndexFlatL2(dim)

        chunks_index.add(embeddings)

        all_metadata = existing_metadata + new_chunks

        faiss.write_index(chunks_index, chunks_index_path)
        np.save(chunks_metadata_path, all_metadata)

        return all_metadata, new_chunks

    def _parse_code_chunks(self, code: str, filepath: str) -> List[Dict[str, Any]]:
        try:
            tree = ast.parse(code)
            chunks = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    chunk = {
                        'type': 'function',
                        'name': node.name,
                        'lineno': node.lineno,
                        'end_lineno': getattr(node, 'end_lineno', node.lineno),
                        'code': self._extract_code_segment(code, node.lineno, getattr(node, 'end_lineno', node.lineno)),
                        'filepath': filepath
                    }
                    chunks.append(chunk)
                elif isinstance(node, ast.ClassDef):
                    chunk = {
                        'type': 'class',
                        'name': node.name,
                        'lineno': node.lineno,
                        'end_lineno': getattr(node, 'end_lineno', node.lineno),
                        'code': self._extract_code_segment(code, node.lineno, getattr(node, 'end_lineno', node.lineno)),
                        'filepath': filepath
                    }
                    chunks.append(chunk)

            return chunks
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
            return []

    def _extract_code_segment(self, code: str, start_line: int, end_line: int) -> str:
        lines = code.split('\n')
        return '\n'.join(lines[start_line-1:end_line])

    def search_code_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        chunks_index_path = os.path.join(self.storage_dir, 'chunks_index.faiss')
        chunks_metadata_path = os.path.join(self.storage_dir, 'chunks_metadata.npy')

        if not os.path.exists(chunks_index_path) or not os.path.exists(chunks_metadata_path):
            return []

        chunks_index = faiss.read_index(chunks_index_path)
        metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

        # Search with a larger k to ensure we get the target function even if it has lower base similarity
        # We'll boost the scores and then trim to top_k after scoring
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
                chunk_name_lower = chunk_meta['name'].lower()

                chunk_name_boost_exact = float(os.getenv("CHUNK_NAME_BOOST_EXACT", "0.8"))
                chunk_name_boost_partial = float(os.getenv("CHUNK_NAME_BOOST_PARTIAL", "0.4"))

                # Highest priority: exact function name match in query words
                # Use exact equality to avoid substring matches (e.g., get_todo vs get_todo_file_path)
                if chunk_name_lower in query_words:
                    boost = chunk_name_boost_exact
                # Partial boost only if function name is substring AND it's not a false positive
                # We check that the match is either at word boundaries or complete
                elif chunk_name_lower in query.lower():
                    # Only apply partial boost if it's not a subset of another word in query_words
                    # e.g., don't boost "get_todo_file_path" if "get_todo" was specifically mentioned
                    is_false_positive = any(
                        word != chunk_name_lower and word in chunk_name_lower
                        for word in query_words
                    )
                    if not is_false_positive:
                        boost = chunk_name_boost_partial

                similarity = min(similarity + boost, 1.0)

                results.append({
                    'chunk_id': chunk_meta['chunk_id'],
                    'filename': chunk_meta['filename'],
                    'type': chunk_meta['type'],
                    'name': chunk_meta['name'],
                    'lineno': chunk_meta['lineno'],
                    'end_lineno': chunk_meta['end_lineno'],
                    'code': chunk_meta['code'],
                    'similarity': similarity
                })

        results.sort(key=lambda item: item['similarity'], reverse=True)
        # Return only the top_k results after applying boosts and sorting
        return results[:top_k]

    def find_functions_by_name(self, function_name: str) -> List[Dict[str, Any]]:
        chunks_metadata_path = os.path.join(self.storage_dir, 'chunks_metadata.npy')

        if not os.path.exists(chunks_metadata_path):
            return []

        metadata = np.load(chunks_metadata_path, allow_pickle=True).tolist()

        matching_functions = []
        for chunk_meta in metadata:
            if chunk_meta['type'] == 'function' and chunk_meta['name'] == function_name:
                matching_functions.append(chunk_meta)

        return matching_functions
