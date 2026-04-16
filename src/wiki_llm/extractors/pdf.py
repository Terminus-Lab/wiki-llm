from pathlib import Path

import pymupdf


def extract(filePath: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF."""

    doc = pymupdf.open(str(filePath))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)
