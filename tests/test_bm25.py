from datetime import date
from pathlib import Path

import pytest

from wiki_llm.indexing.bm25 import BM25Index, SearchResult
from wiki_llm.wiki.reader import WikiPage


def make_page(tmp_path: Path, name: str, title: str, body: str, tags: list[str] = []) -> WikiPage:
    return WikiPage(
        path=tmp_path / f"{name}.md",
        title=title,
        type="concept",
        tags=tags,
        sources=[],
        related=[],
        created=date(2026, 4, 1),
        updated=date(2026, 4, 11),
        body=body,
    )


@pytest.fixture
def idx(tmp_path):
    with BM25Index(tmp_path / ".indexes" / "fts.db") as index:
        yield index


@pytest.fixture
def populated(idx, tmp_path):
    pages = [
        make_page(tmp_path, "transformers", "Transformer Architecture",
                  "The transformer uses self-attention to process sequences in parallel.",
                  tags=["nlp", "deep-learning"]),
        make_page(tmp_path, "attention", "Attention Mechanism",
                  "Attention allows the model to focus on relevant parts of the input.",
                  tags=["nlp"]),
        make_page(tmp_path, "bert", "BERT",
                  "BERT is a bidirectional transformer pretrained on masked language modeling.",
                  tags=["nlp", "pretraining"]),
        make_page(tmp_path, "faiss", "FAISS",
                  "FAISS is a library for efficient similarity search over dense vectors.",
                  tags=["vector-search"]),
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
    results = idx.search("attention", top_k=5)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_top_k_respected(populated):
    idx, _ = populated
    results = idx.search("transformer nlp", top_k=2)
    assert len(results) <= 2


def test_search_scores_are_positive(populated):
    idx, _ = populated
    results = idx.search("attention")
    assert all(r.score > 0 for r in results)


def test_search_best_match_first(populated):
    idx, _ = populated
    results = idx.search("attention mechanism")
    titles = [r.title for r in results]
    # "Attention Mechanism" page should rank first
    assert titles[0] == "Attention Mechanism"


def test_search_no_match_returns_empty(populated):
    idx, _ = populated
    results = idx.search("quantum entanglement")
    assert results == []


def test_search_by_tag(populated):
    idx, _ = populated
    results = idx.search("vector-search")
    assert any(r.title == "FAISS" for r in results)


# --- upsert / delete ---

def test_upsert_updates_existing(idx, tmp_path):
    page = make_page(tmp_path, "p1", "Original Title", "Original body.")
    idx.upsert(page)

    updated = page.model_copy(update={"title": "Updated Title", "body": "Updated body."})
    idx.upsert(updated)

    assert idx.count() == 1  # still one record
    results = idx.search("Updated")
    assert results[0].title == "Updated Title"


def test_delete_removes_page(idx, tmp_path):
    page = make_page(tmp_path, "p1", "To Delete", "Will be removed.")
    idx.upsert(page)
    assert idx.count() == 1

    idx.delete(page.path)
    assert idx.count() == 0
    assert idx.search("removed") == []


def test_delete_nonexistent_is_safe(idx, tmp_path):
    idx.delete(tmp_path / "ghost.md")  # should not raise


# --- db location ---

def test_creates_db_file(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "fts.db"
    with BM25Index(db_path) as idx:
        assert db_path.exists()
