from pathlib import Path

from wiki_llm.exceptions import UnsupportedFileType
from wiki_llm.extractors import html, markdown, pdf, plaintext

_EXTRACTORS = {
    ".md": markdown.extract,
    ".txt": plaintext.extract,
    ".csv": plaintext.extract,
    ".json": plaintext.extract,
    ".pdf": pdf.extract,
    ".html": html.extract,
    ".htm": html.extract,
}


def extract(path: Path) -> str:
    """Dispatch to the correct extractor based on file extension."""
    ext = path.suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise UnsupportedFileType(path, ext)
    return extractor(path)


def supported_extensions() -> list[str]:
    return list(_EXTRACTORS.keys())
