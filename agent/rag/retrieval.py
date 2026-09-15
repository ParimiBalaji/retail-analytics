import os
import glob
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from nltk.tokenize import word_tokenize
import nltk

# Ensure we have the tokenizer (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt_tab') # Updated for newer nltk versions
    nltk.download('punkt')

class LocalRetriever:
    def __init__(self, docs_path: str = "docs"):
        self.docs_path = docs_path
        self.chunks: List[Dict[str, Any]] = []
        self.bm25 = None
        
        # 1. Load and Index immediately
        self._load_documents()
        self._build_index()

    def _load_documents(self):
        """
        Reads all .md files in docs/, splits by double newline (paragraphs),
        and stores them with unique IDs.
        """
        md_files = glob.glob(os.path.join(self.docs_path, "*.md"))
        
        for filepath in md_files:
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple chunking strategy: Split by double newlines (paragraphs)
            raw_chunks = content.split("\n\n")
            
            for i, text in enumerate(raw_chunks):
                if text.strip():  # Skip empty chunks
                    chunk_id = f"{filename}::chunk{i}"
                    self.chunks.append({
                        "id": chunk_id,
                        "content": text.strip(),
                        "source": filename
                    })
        
        print(f"Loaded {len(self.chunks)} chunks from {len(md_files)} files.")

    def _build_index(self):
        """
        Creates the BM25 index from the loaded chunks.
        """
        if not self.chunks:
            print("Warning: No documents found to index!")
            return

        # Tokenize corpus for BM25
        tokenized_corpus = [self._tokenize(chunk["content"]) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _tokenize(self, text: str) -> List[str]:
        try:
            return word_tokenize(text.lower())
        except Exception:
            return [w for w in text.lower().replace("\n", " ").split(" ") if w.strip()]

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Returns the top_k chunks relevant to the query.
        """
        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        # Get scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sort by score descending
        # We zip indices with scores, sort, and take top k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx].copy()
            chunk["score"] = float(scores[idx]) # Add score for debugging
            results.append(chunk)
            
        return results

# Self-test block
if __name__ == "__main__":
    retriever = LocalRetriever()
    hits = retriever.retrieve("return policy for beverages")
    for hit in hits:
        print(f"[{hit['score']:.2f}] {hit['id']}: {hit['content'][:50]}...")