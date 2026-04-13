from datetime import date

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


def test_write_create_files(sample_page) -> None:
    write_page(sample_page)
    assert sample_page.path.exists(), f"Expected file to exist at {sample_page.path}"


def test_write_no_tmp_file_left(sample_page) -> None:
    write_page(sample_page)
    tmp_file = list(sample_page.path.parent.glob("*.tmp"))
    assert tmp_file == [], "No tmp files left on the disk"


def test_write_read(sample_page) -> None:
    write_page(sample_page)
    loaded_page = read_page(sample_page.path)

    assert loaded_page.title == sample_page.title
    assert loaded_page.type == sample_page.type
    assert loaded_page.tags == sample_page.tags
    assert loaded_page.sources == sample_page.sources
    assert loaded_page.related == sample_page.related
    assert loaded_page.created == sample_page.created
    assert loaded_page.updated == sample_page.updated
    assert loaded_page.body.strip() == sample_page.body.strip()


def test_overwrite_existing(sample_page) -> None:
    write_page(sample_page)

    updated = sample_page.model_copy(
        update={
            "title": "Attention Mechanism (revised)",
            "updated": date(2024, 6, 4),
        }
    )
    write_page(updated)

    loaded_page = read_page(sample_page.path)
    assert loaded_page.title == "Attention Mechanism (revised)", (
        "Page title should be: Attention Mechanism (revised)"
    )

    assert loaded_page.updated == date(2024, 6, 4), "Date should be updated"


def test_creates_parent_dirs(tmp_path) -> None:
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

    write_page(page=page)
    assert page.path.exists(), f"New wiki page should be created in {page.path}"


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
