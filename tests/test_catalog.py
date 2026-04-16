from datetime import date
from pathlib import Path

import pytest

from wiki_llm.wiki.catalog import read_catalog_text, rebuild_catalog
from wiki_llm.wiki.reader import WikiPage
from wiki_llm.wiki.writer import write_page


def make_page(wiki_dir: Path, name: str, title: str, type_: str, tags: list[str]) -> WikiPage:
    page = WikiPage(
        path=wiki_dir / f"{name}.md",
        title=title,
        type=type_,
        tags=tags,
        sources=[],
        related=[],
        created=date(2026, 4, 1),
        updated=date(2026, 4, 11),
        body="Body text.",
    )
    write_page(page)
    return page


def test_rebuild_creates_index_md(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    make_page(wiki_dir, "attention", "Attention Mechanism", "concept", ["nlp"])
    index_md = tmp_path / "index.md"

    rebuild_catalog(wiki_dir, index_md)
    assert index_md.exists()


def test_rebuild_contains_page_titles(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    make_page(wiki_dir, "attention", "Attention Mechanism", "concept", ["nlp"])
    make_page(wiki_dir, "bert", "BERT", "entity", ["nlp", "pretraining"])
    index_md = tmp_path / "index.md"

    rebuild_catalog(wiki_dir, index_md)
    content = index_md.read_text()
    assert "Attention Mechanism" in content
    assert "BERT" in content


def test_rebuild_contains_page_count(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    for i in range(3):
        make_page(wiki_dir, f"page{i}", f"Page {i}", "concept", [])
    index_md = tmp_path / "index.md"

    rebuild_catalog(wiki_dir, index_md)
    assert "3 pages" in index_md.read_text()


def test_rebuild_empty_wiki(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    index_md = tmp_path / "index.md"

    rebuild_catalog(wiki_dir, index_md)
    content = index_md.read_text()
    assert "0 pages" in content


def test_read_catalog_text_returns_content(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    make_page(wiki_dir, "p1", "Page One", "concept", ["tag1"])
    index_md = tmp_path / "index.md"
    rebuild_catalog(wiki_dir, index_md)

    text = read_catalog_text(index_md)
    assert "Page One" in text


def test_read_catalog_text_missing_file(tmp_path):
    text = read_catalog_text(tmp_path / "index.md")
    assert "no pages" in text.lower()
