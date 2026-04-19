from pathlib import Path

import pytest

from wiki_llm.wiki.log import append_log


def test_append_creates_log_file(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/doc.pdf"), created=[Path("wiki/page.md")], updated=[])
    assert log.exists()


def test_append_contains_source(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/paper.pdf"), created=[], updated=[])
    assert "raw/paper.pdf" in log.read_text()


def test_append_lists_created_pages(tmp_path):
    log = tmp_path / "log.md"
    append_log(
        log,
        Path("raw/doc.pdf"),
        created=[Path("wiki/attention.md"), Path("wiki/transformer.md")],
        updated=[],
    )
    content = log.read_text()
    assert "attention.md" in content
    assert "transformer.md" in content


def test_append_lists_updated_pages(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/doc.pdf"), created=[], updated=[Path("wiki/bert.md")])
    assert "bert.md" in log.read_text()


def test_append_is_additive(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/first.pdf"), created=[Path("wiki/a.md")], updated=[])
    append_log(log, Path("raw/second.pdf"), created=[Path("wiki/b.md")], updated=[])
    content = log.read_text()
    assert "first.pdf" in content
    assert "second.pdf" in content


def test_append_contains_timestamp(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/doc.pdf"), created=[], updated=[])
    # Timestamp format: ## 2026-04-16T14:30:00Z
    import re
    assert re.search(r"## \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", log.read_text())


def test_omits_created_section_when_empty(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/doc.pdf"), created=[], updated=[Path("wiki/p.md")])
    assert "Created" not in log.read_text()


def test_omits_updated_section_when_empty(tmp_path):
    log = tmp_path / "log.md"
    append_log(log, Path("raw/doc.pdf"), created=[Path("wiki/p.md")], updated=[])
    assert "Updated" not in log.read_text()
