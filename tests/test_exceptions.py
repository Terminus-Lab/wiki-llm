from datetime import date
from pathlib import Path

import pytest

from wiki_llm.exceptions import (
    WikiIndexError,
    PageNotFound,
    PageParseError,
    UnsupportedFileType,
    WikiError,
)
from wiki_llm.extractors.dispatcher import extract
from wiki_llm.indexing.bm25 import BM25Index
from wiki_llm.wiki.reader import read_page


# --- hierarchy ---

def test_all_errors_are_wiki_error():
    assert issubclass(PageNotFound, WikiError)
    assert issubclass(PageParseError, WikiError)
    assert issubclass(UnsupportedFileType, WikiError)
    assert issubclass(WikiIndexError, WikiError)


# --- PageNotFound ---

def test_read_missing_file_raises_page_not_found(tmp_path):
    with pytest.raises(PageNotFound) as exc_info:
        read_page(tmp_path / "ghost.md")
    assert "ghost.md" in str(exc_info.value)


def test_page_not_found_carries_path(tmp_path):
    path = tmp_path / "ghost.md"
    with pytest.raises(PageNotFound) as exc_info:
        read_page(path)
    assert exc_info.value.path == path


# --- PageParseError ---

def test_missing_required_field_raises_page_parse_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: No Type Here\ncreated: 2026-04-11\nupdated: 2026-04-11\n---\nBody.\n")
    with pytest.raises(PageParseError) as exc_info:
        read_page(bad)
    assert exc_info.value.path == bad


def test_invalid_type_value_raises_page_parse_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: Bad\ntype: unknown\ncreated: 2026-04-11\nupdated: 2026-04-11\n---\nBody.\n")
    with pytest.raises(PageParseError):
        read_page(bad)


# --- UnsupportedFileType ---

def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "file.docx"
    f.write_text("data")
    with pytest.raises(UnsupportedFileType) as exc_info:
        extract(f)
    assert exc_info.value.ext == ".docx"
    assert exc_info.value.path == f


def test_unsupported_file_type_is_wiki_error(tmp_path):
    f = tmp_path / "file.xyz"
    f.write_text("data")
    with pytest.raises(WikiError):
        extract(f)


# --- WikiIndexError ---

def test_index_error_on_corrupt_db(tmp_path):
    db_path = tmp_path / "fts.db"
    db_path.write_bytes(b"not a sqlite database")
    with pytest.raises(WikiIndexError):
        BM25Index(db_path)
