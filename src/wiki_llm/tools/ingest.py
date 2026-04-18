from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from wiki_llm.config import Settings, settings as _global_settings
from wiki_llm.exceptions import PageNotFound
from wiki_llm.extractors.dispatcher import extract
from wiki_llm.indexing.bm25 import BM25Index
from wiki_llm.indexing.embeddings import EmbeddingIndex
from wiki_llm.llm.client import IngestResponse, LLMClient
from wiki_llm.wiki.catalog import read_catalog_text, rebuild_catalog
from wiki_llm.wiki.log import append_log
from wiki_llm.wiki.reader import WikiPage, read_page
from wiki_llm.wiki.writer import write_page

_DEFAULT_SCHEMA = """\
# Wiki schema

## Page types
- entity: a specific thing (person, org, model, tool)
- concept: an idea or technique
- summary: a summary of a single source document

## Naming conventions
- Use lowercase, hyphen-separated slugs for page filenames
- Prefer specific, descriptive titles
- Use [[page-name]] syntax for cross-references

## Structure
Every page has YAML frontmatter: title, type, tags, sources, related, created, updated.
Body is markdown. Use ## sections to break up long content.
"""


@dataclass
class IngestResult:
    raw_path: Path
    created: list[Path] = field(default_factory=list)
    updated: list[Path] = field(default_factory=list)
    summary: str = ""


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _copy_to_raw(source: Path, raw_dir: Path) -> Path:
    dest = raw_dir / source.name
    counter = 1
    while dest.exists():
        dest = raw_dir / f"{source.stem}-{counter}{source.suffix}"
        counter += 1
    shutil.copy2(str(source), str(dest))
    return dest


def _build_summary_body(response: IngestResponse) -> str:
    parts = [response.summary]
    if response.claims:
        parts.append("\n## Key claims\n")
        parts.extend(f"- {c}" for c in response.claims)
    return "\n".join(parts)


def run_ingest(
    source_path: str | Path,
    guidance: str = "",
    *,
    cfg: Settings | None = None,
    _llm_client: LLMClient | None = None,
    _embedding_model=None,
) -> IngestResult:
    """Ingest a source file into the wiki.

    Args:
        source_path:      Path to the source file.
        guidance:         Optional hint to the LLM (e.g. "focus on methodology").
        cfg:              Settings override (uses global settings if None).
        _llm_client:      Injected LLMClient for testing.
        _embedding_model: Injected encoder for EmbeddingIndex (avoids model download in tests).
    """
    cfg = cfg or _global_settings
    client = _llm_client or LLMClient(model=cfg.llm_model, api_key=cfg.llm_api_key)

    source = Path(source_path)
    if not source.exists():
        raise PageNotFound(source)

    # 1. Copy source to raw/ (immutable archive)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = _copy_to_raw(source, cfg.raw_dir)

    # 2. Extract plain text
    text = extract(raw_path)

    # 3. Read schema + catalog context for the LLM
    schema_text = cfg.schema_md.read_text() if cfg.schema_md.exists() else _DEFAULT_SCHEMA
    index_text = read_catalog_text(cfg.index_md)

    # 4. LLM extraction
    response = client.extract(text, schema_text, index_text, guidance=guidance)

    # 5. Write wiki pages
    cfg.wiki_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    created: list[Path] = []
    updated: list[Path] = []

    all_items = response.entities + response.concepts

    # Summary page for this source
    source_slug = _slugify(source.stem)
    summary_path = cfg.wiki_dir / f"summary--{source_slug}.md"
    related_slugs = [_slugify(item.name) for item in all_items]

    if summary_path.exists():
        existing = read_page(summary_path)
        write_page(existing.model_copy(update={
            "updated": today,
            "body": existing.body + f"\n\n{_build_summary_body(response)}",
        }))
        updated.append(summary_path)
    else:
        write_page(WikiPage(
            path=summary_path,
            title=f"Summary: {source.name}",
            type="summary",
            tags=[],
            sources=[str(raw_path)],
            related=related_slugs,
            created=today,
            updated=today,
            body=_build_summary_body(response),
        ))
        created.append(summary_path)

    # Entity and concept pages
    for item in all_items:
        slug = _slugify(item.name)
        page_path = cfg.wiki_dir / f"{slug}.md"
        item_related = [_slugify(r) for r in item.related]

        if page_path.exists():
            existing = read_page(page_path)
            merged_sources = list(dict.fromkeys(existing.sources + [str(raw_path)]))
            merged_related = list(dict.fromkeys(existing.related + item_related))
            write_page(existing.model_copy(update={
                "updated": today,
                "sources": merged_sources,
                "related": merged_related,
                "body": existing.body + f"\n\n{item.description}",
            }))
            updated.append(page_path)
        else:
            write_page(WikiPage(
                path=page_path,
                title=item.name,
                type=item.type,
                tags=item.tags,
                sources=[str(raw_path)],
                related=item_related,
                created=today,
                updated=today,
                body=item.description,
            ))
            created.append(page_path)

    # 6. Re-index all changed pages
    all_changed = created + updated
    if all_changed:
        cfg.indexes_dir.mkdir(parents=True, exist_ok=True)
        with BM25Index(cfg.indexes_dir / "fts.db") as bm25:
            for path in all_changed:
                bm25.upsert(read_page(path))

        vec = EmbeddingIndex(cfg.indexes_dir, model=_embedding_model)
        for path in all_changed:
            vec.upsert(read_page(path))

    # 7. Rebuild catalog
    rebuild_catalog(cfg.wiki_dir, cfg.index_md)

    # 8. Append log entry
    append_log(cfg.log_md, raw_path, created, updated)

    return IngestResult(
        raw_path=raw_path,
        created=created,
        updated=updated,
        summary=response.summary,
    )
