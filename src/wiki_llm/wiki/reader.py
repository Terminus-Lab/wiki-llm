from datetime import date
from pathlib import Path
from typing import Literal
import frontmatter
from pydantic import BaseModel, ValidationError

from wiki_llm.exceptions import PageNotFound, PageParseError


PageType = Literal["entity", "summary", "concept", "comparison", "analysis"]


class WikiPage(BaseModel):
    path: Path
    title: str
    type: PageType
    tags: list[str] = []
    sources: list[str] = []
    related: list[str] = []
    created: date
    updated: date
    body: str


def read_page(path: Path) -> WikiPage:
    """Parse a single wiki page from a markdown file with YAML frontmatter."""

    if not path.exists():
        raise PageNotFound(path)

    try:
        post = frontmatter.load(str(path))
        return WikiPage(
            path=path,
            title=post["title"],
            type=post["type"],
            tags=post.get("tags", []),
            sources=post.get("sources", []),
            related=post.get("related", []),
            created=post["created"],
            updated=post["updated"],
            body=post.content,
        )
    except (KeyError, ValidationError) as ex:
        raise PageParseError(path=path, reason=str(ex))


def read_all_pages(wiki_dir: Path) -> list[WikiPage]:
    """Read all .md pages from a wiki directory."""
    return [read_page(p) for p in sorted(wiki_dir.glob("*.md"))]
