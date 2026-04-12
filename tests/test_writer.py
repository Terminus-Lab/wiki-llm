from datetime import date
from pathlib import Path

import pytest

from wiki_llm.wiki.reader import WikiPage, read_page
from wiki_llm.wiki.writer import write_page


@pytest.fixture
def sample_page(tmp_path):
    return WikiPage(
        path=tmp_path / "attention-mechanism.md",
        title="Attention Mechanism",
        type="concept",
        tags=["machine-learning", "nlp"],
        sources=["raw/attention-paper.pdf"],
        related=["transformer-architecture"],
        created=date(2026, 4, 1),
        updated=date(2026, 4, 11),
        body="# Attention Mechanism\n\nFocuses on relevant input parts.\n",
    )


def test_write_creates_file(sample_page):
    write_page(sample_page)
    assert sample_page.path.exists()


def test_write_no_tmp_file_left(sample_page):
    write_page(sample_page)
    tmp_files = list(sample_page.path.parent.glob("*.tmp"))
    assert tmp_files == []


def test_round_trip(sample_page):
    write_page(sample_page)
    loaded = read_page(sample_page.path)

    assert loaded.title == sample_page.title
    assert loaded.type == sample_page.type
    assert loaded.tags == sample_page.tags
    assert loaded.sources == sample_page.sources
    assert loaded.related == sample_page.related
    assert loaded.created == sample_page.created
    assert loaded.updated == sample_page.updated
    assert loaded.body.strip() == sample_page.body.strip()


def test_overwrite_existing(sample_page):
    write_page(sample_page)

    updated = sample_page.model_copy(
        update={"title": "Attention Mechanism (revised)", "updated": date(2026, 4, 12)}
    )
    write_page(updated)

    loaded = read_page(sample_page.path)
    assert loaded.title == "Attention Mechanism (revised)"
    assert loaded.updated == date(2026, 4, 12)


def test_creates_parent_dirs(tmp_path):
    page = WikiPage(
        path=tmp_path / "wiki" / "sub" / "page.md",
        title="Nested",
        type="entity",
        tags=[],
        sources=[],
        related=[],
        created=date(2026, 4, 11),
        updated=date(2026, 4, 11),
        body="Body.\n",
    )
    write_page(page)
    assert page.path.exists()


def test_optional_fields_round_trip(tmp_path):
    page = WikiPage(
        path=tmp_path / "minimal.md",
        title="Minimal",
        type="entity",
        created=date(2026, 4, 11),
        updated=date(2026, 4, 11),
        body="Body.\n",
    )
    write_page(page)
    loaded = read_page(page.path)
    assert loaded.tags == []
    assert loaded.sources == []
    assert loaded.related == []
