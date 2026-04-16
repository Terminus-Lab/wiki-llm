from pathlib import Path


def extract(filePath: Path) -> str:
    """Markdown passthrough - return content as it is"""
    return filePath.read_text(encoding="utf-8")
