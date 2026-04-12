from pathlib import Path

import pymupdf


def extract(path: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
    with pymupdf.open(str(path)) as doc:
        return "\n".join(page.get_text() for page in doc)
