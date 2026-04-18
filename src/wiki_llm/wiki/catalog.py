from __future__ import annotations

from pathlib import Path

from wiki_llm.wiki.reader import read_all_pages


def rebuild_catalog(wiki_dir: Path, index_md: Path) -> None:
    """Scan wiki_dir and rewrite index.md with the current page table."""
    pages = read_all_pages(wiki_dir)

    lines = [
        "# Wiki Index\n",
        f"{len(pages)} page{'s' if len(pages) != 1 else ''} total.\n",
        "",
        "| Title | File | Type | Tags |",
        "|-------|------|------|------|",
    ]

    for page in pages:
        tags = ", ".join(page.tags) if page.tags else "—"
        rel = page.path.name
        lines.append(f"| {page.title} | {rel} | {page.type} | {tags} |")

    index_md.parent.mkdir(parents=True, exist_ok=True)
    index_md.write_text("\n".join(lines) + "\n")


def read_catalog_text(index_md: Path) -> str:
    """Return raw index.md text for injection into LLM prompts."""
    if not index_md.exists():
        return "(no pages indexed yet)"
    return index_md.read_text(encoding="utf-8")
