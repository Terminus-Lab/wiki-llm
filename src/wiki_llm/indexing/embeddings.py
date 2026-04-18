import json
from pathlib import Path
from typing import Protocol
import faiss
import numpy as np

from wiki_llm.indexing import SearchResult
from wiki_llm.wiki.reader import WikiPage


class _Encoder(Protocol):
    """Minimal interface needed from SentenceTransformer (enables test mocking)."""

    def get_sentence_embedding_dimension(self) -> int: ...

    def encode(self, sentence: list[str], normalized_embeddings: bool = True) -> np: ...


class EmbeddingIndex:
    """FAISS-backed vector index. One embedding per wiki page."""

    def __init__(
        self,
        index_dir: Path,
        model: _Encoder | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:

        try:
            index_dir.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            raise IndexError(str(err)) from err

        self.faiss_path = index_dir / "vector.faiss"
        self.meta_path = index_dir / "vectors_meta.json"

        if model is not None:
            self._model = model
        else:
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(model_name)
            except Exception as exc:
                raise IndexError("Failed to load embedding model") from exc

        self._dim: int = self._model.get_sentence_embedding_dimension()

        if self._faiss_path_exists() and self._meta_path.exists():
            self._load()
        else:
            self._index = faiss.IndexFlatIP(self._dim)
            self._meta: list[dict[str, str]] = []

    # --- write ---

    def upsert(self, page: WikiPage) -> None:
        """Embed and index a page, replacing any previous entry for that path."""
        path_str = str(page.path)

        existing = [i for i, m in enumerate(self._meta) if m["path"] == path_str]
        if existing:
            keep = [i for i in range(len(self._meta)) if i not in set(existing)]
            self._rebuild(keep)
            self._meta = [self._meta[i] for i in keep]

        vec = self._embed(f"{page.title}\n\n{page.body}")
        self._index.add(vec)
        self._meta.append({"path": path_str, "title": page.title})
        self._save()

    def delete(self, page_path: Path) -> None:
        """Remove a page from the index. Silent no-op if not present."""
        path_str = str(page_path)
        keep = [i for i, m in enumerate(self._meta) if m["path"] != path_str]
        if len(keep) == len(self._meta):
            return
        self._rebuild(keep)
        self._meta = [self._meta[i] for i in keep]
        self._save()

    # --- read ---

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Semantic search. Returns results ranked best-first."""
        if self._index.ntotal == 0:
            return []
        k = min(top_k, self._index.ntotal)
        vec = self._embed(query)
        scores, indices = self._index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            m = self._meta[idx]
            results.append(
                SearchResult(path=Path(m["path"]), title=m["title"], score=float(score))
            )
        return results

    def count(self) -> int:
        return self._index.ntotal

    # --- internal ---

    def _embed(self, text: str) -> np.ndarray:
        return self._model.encode([text], normalize_embeddings=True).astype(np.float32)

    def _rebuild(self, keep_indices: list[int]) -> None:
        """Rebuild FAISS index keeping only the rows at keep_indices."""
        if not keep_indices:
            self._index = faiss.IndexFlatIP(self._dim)
            return
        all_vecs = np.zeros((self._index.ntotal, self._dim), dtype=np.float32)
        self._index.reconstruct_n(0, self._index.ntotal, all_vecs)
        kept = all_vecs[keep_indices]
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(kept)

    def _save(self) -> None:
        faiss.write_index(self._index, str(self._faiss_path))
        self._meta_path.write_text(json.dumps(self._meta, indent=2))

    def _load(self) -> None:
        self._index = faiss.read_index(str(self._faiss_path))
        self._meta = json.loads(self._meta_path.read_text())
