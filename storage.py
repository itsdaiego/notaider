import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


model = SentenceTransformer('all-MiniLM-L6-v2')


class Storage():
    def __init__(self, storage_dir='storage'):
        self.storage_dir = storage_dir

    def ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        import os
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def clean_embeddings(self):
        """Clean/reset the FAISS index and filenames - like a database reset."""
        files_to_remove = ['index.faiss', 'filenames.npy']
        removed_files = []
        
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)
                print(f"Removed: {file}")
        
        print("Database reset complete!")

    def store_files(self, files):
        """Store files in the storage directory."""

        index = faiss.read_index('index.faiss')
        filenames = np.load('filenames.npy')
        model = SentenceTransformer('all-MiniLM-L6-v2')

        texts = []
        filenames = []

        files = os.listdir(self.storage_dir)

        # extract content from files
        for file in files:
            with open(file, 'r') as f:
                text = f.read().strip()

                if text:
                    texts.append(text)
                    filenames.append(file)
        
        embeddings = model.encode(texts, convert_to_numpy=True)

        # create index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)  # L2 = Euclidean distance
        index.add(embeddings, filenames)

        # save index and filenames
        faiss.write_index(index, 'index.faiss')
        np.save('filenames.npy', np.array(filenames))

        print(f"Stored {len(filenames)} files in FAISS index.")





