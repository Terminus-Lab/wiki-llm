from __future__ import annotations

from pathlib import Path

from wiki_llm.indexing import SearchResult


def rrf_fuse(
    bm25: list[SearchResult],
    vector: list[SearchResult],
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    k: int = 60,
    top_n: int = 5,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion over BM25 + vector result lists.

    Score for each page = sum of weight/(k + rank) across whichever lists contain it.
    """
    scores: dict[str, float] = {}
    titles: dict[str, str] = {}
    paths: dict[str, Path] = {}

    for rank, r in enumerate(bm25):
        key = str(r.path)
        scores[key] = scores.get(key, 0.0) + bm25_weight / (k + rank + 1)
        titles[key] = r.title
        paths[key] = r.path

    for rank, r in enumerate(vector):
        key = str(r.path)
        scores[key] = scores.get(key, 0.0) + vector_weight / (k + rank + 1)
        titles[key] = r.title
        paths[key] = r.path

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [
        SearchResult(path=paths[key], title=titles[key], score=scores[key])
        for key in sorted_keys
    ]
