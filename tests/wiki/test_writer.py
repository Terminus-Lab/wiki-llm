from datetime import date

import pytest

from wiki_llm.wiki.reader import WikiPage
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
