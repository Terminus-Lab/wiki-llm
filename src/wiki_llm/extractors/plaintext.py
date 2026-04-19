from pathlib import Path


def extract(path: Path) -> str:
    """Plain text passthrough — covers .txt, .csv, .json."""
    return path.read_text(encoding="utf-8")
