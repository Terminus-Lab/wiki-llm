import json
import pytest
from pathlib import Path

from wiki_llm.extractors.dispatcher import extract, supported_extensions
from wiki_llm.extractors import markdown, plaintext, html


# --- markdown ---

def test_markdown_passthrough(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Hello\n\nSome **bold** text.")
    assert extract(f) == "# Hello\n\nSome **bold** text."


# --- plaintext ---

def test_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("plain text content")
    assert extract(f) == "plain text content"


def test_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name,age\nAlice,30\nBob,25")
    assert "Alice" in extract(f)


def test_json(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps({"key": "value"}))
    assert "value" in extract(f)


# --- html ---

def test_html_converts_headings(tmp_path):
    f = tmp_path / "page.html"
    f.write_text("<h1>Title</h1><p>Body text.</p>")
    result = extract(f)
    assert "# Title" in result
    assert "Body text." in result


def test_htm_extension(tmp_path):
    f = tmp_path / "page.htm"
    f.write_text("<p>Hello</p>")
    assert "Hello" in extract(f)


def test_html_strips_tags(tmp_path):
    f = tmp_path / "page.html"
    f.write_text("<div><p>Content <strong>here</strong>.</p></div>")
    result = extract(f)
    assert "<div>" not in result
    assert "Content" in result


# --- pdf ---

def test_pdf_extraction(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from PDF")
    doc.save(str(pdf_path))
    doc.close()

    result = extract(pdf_path)
    assert "Hello from PDF" in result


# --- dispatcher ---

def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "file.docx"
    f.write_text("data")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract(f)


def test_supported_extensions():
    exts = supported_extensions()
    for ext in [".md", ".txt", ".csv", ".json", ".pdf", ".html", ".htm"]:
        assert ext in exts
