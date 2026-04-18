from pathlib import Path

from wiki_llm.indexing import SearchResult
from wiki_llm.indexing.hybrid import rrf_fuse


def sr(name: str, score: float = 1.0) -> SearchResult:
    return SearchResult(path=Path(f"/wiki/{name}.md"), title=name, score=score)


def test_combines_results_from_both_lists():
    bm25 = [sr("a"), sr("b")]
    vec = [sr("c"), sr("d")]
    results = rrf_fuse(bm25, vec, top_n=4)
    names = {r.title for r in results}
    assert {"a", "b", "c", "d"} == names


def test_top_n_respected():
    bm25 = [sr(f"p{i}") for i in range(10)]
    vec = [sr(f"q{i}") for i in range(10)]
    results = rrf_fuse(bm25, vec, top_n=3)
    assert len(results) == 3


def test_deduplicates_same_page():
    bm25 = [sr("shared"), sr("b")]
    vec = [sr("shared"), sr("c")]
    results = rrf_fuse(bm25, vec, top_n=10)
    paths = [r.path for r in results]
    assert len(paths) == len(set(str(p) for p in paths))


def test_shared_page_scores_higher():
    # "shared" appears first in both lists — should beat a page in only one list
    bm25 = [sr("shared"), sr("bm25_only")]
    vec = [sr("shared"), sr("vec_only")]
    results = rrf_fuse(bm25, vec, top_n=3)
    assert results[0].title == "shared"


def test_empty_bm25():
    vec = [sr("a"), sr("b")]
    results = rrf_fuse([], vec, top_n=5)
    assert len(results) == 2
    assert {r.title for r in results} == {"a", "b"}


def test_empty_vector():
    bm25 = [sr("a"), sr("b")]
    results = rrf_fuse(bm25, [], top_n=5)
    assert len(results) == 2


def test_both_empty():
    assert rrf_fuse([], [], top_n=5) == []


def test_scores_descending():
    bm25 = [sr(f"p{i}") for i in range(5)]
    vec = [sr(f"p{i}") for i in range(5, 10)]
    results = rrf_fuse(bm25, vec, top_n=10)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
