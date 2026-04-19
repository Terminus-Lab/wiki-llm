from datetime import date
from pathlib import Path

import numpy as np
import pytest

from wiki_llm.indexing import SearchResult
from wiki_llm.indexing.embeddings import EmbeddingIndex
from wiki_llm.wiki.reader import WikiPage

DIM = 8  # small dimension for tests


class MockEncoder:
    """Deterministic encoder: same text → same unit vector. No model download."""

    def get_sentence_embedding_dimension(self) -> int:
        return DIM

    def encode(self, sentences: list[str], normalize_embeddings: bool = True) -> np.ndarray:
        vecs = []
        for text in sentences:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            v = rng.random(DIM).astype(np.float32)
            if normalize_embeddings:
                v /= np.linalg.norm(v)
            vecs.append(v)
        return np.array(vecs, dtype=np.float32)


def make_page(tmp_path: Path, name: str, title: str, body: str) -> WikiPage:
    return WikiPage(
        path=tmp_path / f"{name}.md",
        title=title,
        type="concept",
        tags=[],
        sources=[],
        related=[],
        created=date(2026, 4, 1),
        updated=date(2026, 4, 11),
        body=body,
    )


@pytest.fixture
def idx(tmp_path):
    return EmbeddingIndex(tmp_path / ".indexes", model=MockEncoder())


@pytest.fixture
def populated(idx, tmp_path):
    pages = [
        make_page(tmp_path, "transformers", "Transformer Architecture",
                  "Self-attention processes sequences in parallel."),
        make_page(tmp_path, "attention", "Attention Mechanism",
                  "Focuses on relevant parts of the input sequence."),
        make_page(tmp_path, "bert", "BERT",
                  "Bidirectional transformer pretrained on masked language modeling."),
        make_page(tmp_path, "faiss", "FAISS",
                  "Efficient similarity search over dense vectors."),
    ]
    for p in pages:
        idx.upsert(p)
    return idx, pages


# --- basic ---

def test_upsert_increases_count(idx, tmp_path):
    assert idx.count() == 0
    idx.upsert(make_page(tmp_path, "p1", "Page One", "Some content."))
    assert idx.count() == 1


def test_search_returns_results(populated):
    idx, _ = populated
    results = idx.search("attention mechanism", top_k=4)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_top_k_respected(populated):
    idx, _ = populated
    results = idx.search("transformer", top_k=2)
    assert len(results) <= 2


def test_search_scores_between_zero_and_one(populated):
    idx, _ = populated
    results = idx.search("attention")
    # Cosine similarity of normalized vectors is in [-1, 1]; relevant results > 0
    assert all(-1.0 <= r.score <= 1.0 for r in results)


def test_search_empty_index_returns_empty(idx):
    assert idx.search("anything") == []


# --- upsert / delete ---

def test_upsert_replaces_existing(idx, tmp_path):
    page = make_page(tmp_path, "p1", "Original", "Original body.")
    idx.upsert(page)
    assert idx.count() == 1

    updated = page.model_copy(update={"title": "Updated", "body": "Updated body."})
    idx.upsert(updated)
    assert idx.count() == 1  # still one entry

    results = idx.search("Updated body")
    assert results[0].title == "Updated"


def test_delete_removes_entry(idx, tmp_path):
    page = make_page(tmp_path, "p1", "To Delete", "Will be removed.")
    idx.upsert(page)
    assert idx.count() == 1

    idx.delete(page.path)
    assert idx.count() == 0


def test_delete_nonexistent_is_noop(idx, tmp_path):
    idx.delete(tmp_path / "ghost.md")  # must not raise


# --- persistence ---

def test_save_and_reload(tmp_path):
    index_dir = tmp_path / ".indexes"
    page = make_page(tmp_path, "p1", "Persisted Page", "Important content.")

    idx1 = EmbeddingIndex(index_dir, model=MockEncoder())
    idx1.upsert(page)

    # Reload from disk
    idx2 = EmbeddingIndex(index_dir, model=MockEncoder())
    assert idx2.count() == 1
    results = idx2.search("important content")
    assert results[0].title == "Persisted Page"


def test_index_files_created(tmp_path):
    index_dir = tmp_path / ".indexes"
    idx = EmbeddingIndex(index_dir, model=MockEncoder())
    idx.upsert(make_page(tmp_path, "p1", "Test", "Body."))
    assert (index_dir / "vectors.faiss").exists()
    assert (index_dir / "vectors_meta.json").exists()
