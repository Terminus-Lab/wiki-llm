from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    path: Path
    title: str
    score: float  # higher is better
