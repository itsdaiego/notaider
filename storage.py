import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


model = SentenceTransformer('all-MiniLM-L6-v2')


class Storage():
    def __init__(self, storage_dir='db', app_dir='app'):
        self.storage_dir = storage_dir
        self.app_dir = app_dir

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
            with open(file_path, 'r') as f:
                text = f.read().strip()

                if text:
                    texts.append(text)
                    filenames.append(file)
        
        if not texts:
            print("No files with content found to process.")
            return existing_filenames

        embeddings = model.encode(texts, convert_to_numpy=True)

        dim = embeddings.shape[1]
        
        if index is None:
            index = faiss.IndexFlatL2(dim)
        
        index.add(embeddings)
        
        all_filenames = existing_filenames + filenames

        faiss.write_index(index, index_path)
        np.save(filenames_path, np.array(all_filenames))

        return all_filenames
