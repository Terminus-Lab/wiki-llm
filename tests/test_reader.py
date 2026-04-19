import pytest
from datetime import date
from pathlib import Path

from wiki_llm.wiki.reader import WikiPage, read_page, read_all_pages


SAMPLE_PAGE = """\
---
title: "Attention Mechanism"
type: concept
tags: [machine-learning, nlp, transformers]
sources: [raw/attention-paper.pdf]
related: [transformer-architecture, positional-encoding]
created: 2026-04-01
updated: 2026-04-11
---

# Attention Mechanism

Attention allows the model to focus on relevant parts of the input.

## See also

- [[transformer-architecture]]
"""


@pytest.fixture
def page_file(tmp_path):
    p = tmp_path / "attention-mechanism.md"
    p.write_text(SAMPLE_PAGE)
    return p


def test_read_page_fields(page_file):
    page = read_page(page_file)
    assert page.title == "Attention Mechanism"
    assert page.type == "concept"
    assert page.tags == ["machine-learning", "nlp", "transformers"]
    assert page.sources == ["raw/attention-paper.pdf"]
    assert page.related == ["transformer-architecture", "positional-encoding"]
    assert page.created == date(2026, 4, 1)
    assert page.updated == date(2026, 4, 11)


def test_read_page_body(page_file):
    page = read_page(page_file)
    assert "Attention allows the model" in page.body
    assert "[[transformer-architecture]]" in page.body
    # frontmatter should not appear in body
    assert "title:" not in page.body


def test_read_page_path(page_file):
    page = read_page(page_file)
    assert page.path == page_file


def test_read_page_optional_fields_default(tmp_path):
    minimal = tmp_path / "minimal.md"
    minimal.write_text("""\
---
title: "Minimal"
type: entity
created: 2026-04-11
updated: 2026-04-11
---

Body text.
""")
    page = read_page(minimal)
    assert page.tags == []
    assert page.sources == []
    assert page.related == []


def test_invalid_type_raises(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("""\
---
title: "Bad"
type: unknown
created: 2026-04-11
updated: 2026-04-11
---

Body.
""")
    with pytest.raises(Exception):
        read_page(bad)


def test_read_all_pages(tmp_path):
    for name in ["alpha.md", "beta.md", "gamma.md"]:
        (tmp_path / name).write_text(f"""\
---
title: "{name}"
type: concept
created: 2026-04-11
updated: 2026-04-11
---

Body.
""")
    pages = read_all_pages(tmp_path)
    assert len(pages) == 3
    assert [p.title for p in pages] == ["alpha.md", "beta.md", "gamma.md"]


def test_read_all_pages_empty_dir(tmp_path):
    assert read_all_pages(tmp_path) == []
