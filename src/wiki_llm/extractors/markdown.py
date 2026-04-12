from pathlib import Path


def extract(path: Path) -> str:
    """Markdown passthrough — return file contents as-is."""
    return path.read_text(encoding="utf-8")
