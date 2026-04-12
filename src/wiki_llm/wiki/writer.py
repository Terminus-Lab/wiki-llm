from __future__ import annotations

import tempfile
from pathlib import Path

import frontmatter

from wiki_llm.wiki.reader import WikiPage


def write_page(page: WikiPage) -> None:
    """Atomically write a WikiPage to disk using tmp+rename.

    Writes to a temp file in the same directory, then renames to the final
    path. On POSIX this rename is atomic — a crash mid-write never leaves a
    partial file at the destination.
    """
    post = frontmatter.Post(
        page.body,
        title=page.title,
        type=page.type,
        tags=page.tags,
        sources=page.sources,
        related=page.related,
        created=page.created,
        updated=page.updated,
    )
    content = frontmatter.dumps(post)

    dest = page.path
    dest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=dest.parent,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(content)
        tmp = Path(f.name)

    tmp.replace(dest)
