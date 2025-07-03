import os
import re
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class Storage():
    def __init__(self, storage_dir='db', app_dir='app'):
        self.storage_dir = storage_dir
        self.app_dir = app_dir
        self._model = None  # Lazy loading

    @property
    def model(self):
        """Lazy load the model when first accessed"""
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def clean_embeddings(self):
        """Clean/reset the FAISS index and filenames - like a database reset."""
        files_to_remove = ['index.faiss', 'filenames.npy']

        for file in files_to_remove:
            file_path = os.path.join(self.storage_dir, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed: {file_path}")

        print("Database reset complete!")

    def store_files(self):
        """Store files in the storage directory."""
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

        for file in os.listdir(self.app_dir):
            file_path = os.path.join(self.app_dir, file)
            if file.endswith('.py'):
                with open(file_path, 'r') as f:
                    text = f.read().strip()

                    if text and file not in existing_filenames:
                        texts.append(text)
                        filenames.append(file)

        if not texts:
            print("No files with content found to process.")
            return existing_filenames

        embeddings = self.model.encode(texts, convert_to_numpy=True)

        dim = embeddings.shape[1]

        if index is None:
            index = faiss.IndexFlatL2(dim)

        index.add(embeddings)

        all_filenames = existing_filenames + filenames

        faiss.write_index(index, index_path)
        np.save(filenames_path, np.array(all_filenames))

        return all_filenames

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

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def _perform_similarity_boost(self, filename, query):
        boost = 0.0
        base_filename = filename.replace('.py', '')
        query_lower = query.lower()

        # exact match
        if base_filename.lower() in query_lower:
            boost = max(boost, 0.3)


        # split filename into words and check if any word matches query
        normalized_filename = re.sub(r'[_-]', ' ', base_filename.lower())
        if normalized_filename in query_lower:
            boost = max(boost, 0.25)

        return boost
