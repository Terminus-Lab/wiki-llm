# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP server implementing Karpathy's LLM Wiki pattern: a local, file-based knowledge base where an LLM compiles raw sources into a persistent, interlinked wiki of markdown files. See `spec/spec-v1.md` for the full specification.

Stack: Python, FastAPI, Pydantic Settings, SQLite FTS5, FAISS, sentence-transformers, Anthropic SDK.

## Commands

```bash
# Install dependencies (once venv is set up)
pip install -e ".[dev]"

# Run the server (stdio transport)
python server.py

# Run the server (SSE transport)
WIKI_MCP_TRANSPORT=sse python server.py

# Run tests
pytest

# Run a single test file
pytest tests/test_ingest.py

# Run a single test
pytest tests/test_ingest.py::test_name

# Rebuild indexes from scratch
python server.py --rebuild-index

# Lint
ruff check .
```

## Architecture

The server exposes 6 MCP tools (`ingest`, `query`, `lint`, `list_sources`, `list_pages`, `update_schema`) over stdio or SSE transport.

**Data flow for `ingest`:**
1. Source copied to `raw/` (immutable)
2. Extractor (`extractors/`) converts to plain text
3. LLM call receives: extracted text + `schema.md` (wiki conventions) + `index.md` (existing pages catalog)
4. LLM returns structured JSON: `{summary, entities, concepts, claims}`
5. `wiki/writer.py` atomically writes pages via tmp+rename
6. `indexing/bm25.py` (SQLite FTS5) and `indexing/embeddings.py` (FAISS) updated incrementally
7. `index.md` and `log.md` updated last

**Data flow for `query`:**
1. BM25 + vector search → RRF fusion (`indexing/hybrid.py`) → top-k pages
2. LLM synthesizes answer with citations
3. Optionally saved as a new `analysis--*.md` wiki page

**Key design constraints:**
- All wiki writes are atomic (tmp file + rename) — never write directly to final path
- One embedding per wiki page, not per chunk — pages are semantic units
- `schema.md` is injected into every LLM call as the system prompt equivalent
- Wikilinks use `[[page-name]]` syntax; `linker.py` maintains backlink index
- `.indexes/` is gitignored and fully regenerable via `--rebuild-index`

## Workspace layout (runtime)

```
workspace/
  raw/          Immutable source documents
  wiki/         LLM-generated markdown pages
  index.md      Auto-maintained page catalog
  log.md        Append-only operation log
  schema.md     Wiki conventions (injected into every LLM prompt)
  .indexes/     BM25 (fts.db) + vector (vectors.faiss, vectors_meta.json)
```

## Wiki page format

Every page has YAML frontmatter with: `title`, `type` (entity|concept|summary|comparison|analysis), `tags`, `sources`, `related`, `created`, `updated`. Filename convention: `entity-name.md`, `summary--source-name.md`, `compare--a-vs-b.md`, `analysis--topic.md`.

## Configuration

Via `.env` or environment variables (validated by Pydantic Settings in `config.py`):

| Variable | Default | Notes |
|----------|---------|-------|
| `WIKI_WORKSPACE` | `./workspace` | Root directory |
| `WIKI_LLM_PROVIDER` | `anthropic` | `anthropic` \| `openai` \| `ollama` |
| `WIKI_LLM_MODEL` | `claude-sonnet-4-20250514` | |
| `WIKI_LLM_API_KEY` | — | From env |
| `WIKI_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Any sentence-transformers model |
| `WIKI_MCP_TRANSPORT` | `stdio` | `stdio` \| `sse` |
| `WIKI_MCP_PORT` | `8181` | SSE only |
| `WIKI_TOP_K` | `5` | Default retrieval count |
| `WIKI_BM25_WEIGHT` | `0.5` | RRF fusion weight |
| `WIKI_VECTOR_WEIGHT` | `0.5` | RRF fusion weight |

## MVP build order

Follow this sequence — each step is independently testable:

1. `config.py` + `server.py` — FastAPI + MCP stdio transport + workspace init
2. `wiki/reader.py` + `wiki/writer.py` — markdown/frontmatter read/write
3. `tools/ingest.py` — minimal: file → LLM → summary page + index.md
4. `indexing/bm25.py` — SQLite FTS5
5. `tools/query.py` — BM25 search only (no LLM synthesis yet)
6. `indexing/embeddings.py` + `indexing/hybrid.py` — FAISS + RRF fusion
7. `wiki/linker.py` — wikilink resolution + backlink graph
8. `tools/lint.py` — orphans, broken links, stale pages
9. SSE transport
10. LLM-powered query synthesis
