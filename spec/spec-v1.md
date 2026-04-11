# LLM Wiki MCP Server — Spec

## What this is

An MCP server that implements Karpathy's LLM Wiki pattern: a local, file-based knowledge base where an LLM compiles raw sources into a persistent, interlinked wiki of markdown files. The server exposes tools for ingestion, querying (BM25 + vector hybrid search), and maintenance.

Built with FastAPI, Pydantic, and Python. Runs locally. No cloud dependencies.

---

## Architecture overview

```
┌─────────────────────────────────────────────────┐
│  MCP Client (Claude Code, Cursor, etc.)         │
│  Calls tools via stdio or SSE                   │
└──────────────────┬──────────────────────────────┘
                   │ JSON-RPC
┌──────────────────▼──────────────────────────────┐
│  MCP Server (FastAPI)                           │
│                                                 │
│  Tools:                                         │
│    ingest · query · lint · list · update_schema │
│                                                 │
│  Indexing:                                      │
│    BM25 (SQLite FTS5) + Vector (FAISS/numpy)    │
│    Hybrid fusion via RRF                        │
│                                                 │
│  Wiki engine:                                   │
│    Reader · Writer · Linker                     │
└──────────────────┬──────────────────────────────┘
                   │ filesystem
┌──────────────────▼──────────────────────────────┐
│  Workspace (local directory)                    │
│                                                 │
│  raw/          Immutable source documents       │
│  wiki/         LLM-generated markdown pages     │
│  index.md      Auto-maintained page catalog     │
│  log.md        Append-only operation log        │
│  schema.md     Wiki conventions and rules       │
│  .indexes/     BM25 + vector index files        │
└─────────────────────────────────────────────────┘
```

---

## Project structure

```
llm-wiki-mcp/
├── server.py                 # FastAPI app, MCP transport (stdio + SSE)
├── config.py                 # Pydantic Settings: paths, models, thresholds
├── tools/
│   ├── ingest.py             # Ingest a source into the wiki
│   ├── query.py              # Search + synthesize answer
│   ├── lint.py               # Health-check the wiki
│   └── manage.py             # List sources, pages, stats, update schema
├── indexing/
│   ├── bm25.py               # SQLite FTS5 index over wiki pages
│   ├── embeddings.py         # Local embedding model + FAISS index
│   └── hybrid.py             # RRF fusion of BM25 + vector results
├── wiki/
│   ├── reader.py             # Parse markdown + YAML frontmatter
│   ├── writer.py             # Atomic write (tmp + rename)
│   └── linker.py             # [[wikilink]] resolution, backlink graph
├── extractors/
│   ├── markdown.py           # .md passthrough
│   ├── pdf.py                # PDF → text (pymupdf or pdfplumber)
│   ├── plaintext.py          # .txt, .csv, .json
│   └── html.py               # HTML → markdown (markdownify)
└── tests/
    ├── test_ingest.py
    ├── test_query.py
    └── test_lint.py
```

---

## MCP tools

### 1. `ingest`

**Purpose:** Process a raw source into the wiki.

**Input:**
- `source_path` — path to file (relative to workspace or absolute)
- `source_type` — optional override (auto-detected from extension)
- `guidance` — optional human note ("focus on the methodology section")

**Flow:**
1. Copy source to `raw/` (immutable archive)
2. Extract text via appropriate extractor
3. LLM call → extract: summary, entities, concepts, key claims, tags
4. For each entity/concept: create new wiki page or update existing one
5. Update `index.md` with new/changed pages
6. Append entry to `log.md`
7. Re-index changed pages in BM25 + vector indexes

**Output:** List of created/updated wiki pages with brief change summary.

**LLM prompt strategy:** The LLM receives the extracted text + the current `schema.md` (wiki conventions) + the current `index.md` (so it knows what pages exist). It returns structured JSON: `{ summary, entities: [{name, type, description, related}], concepts: [...], claims: [...] }`.

---

### 2. `query`

**Purpose:** Answer a question using the wiki.

**Input:**
- `question` — natural language query
- `top_k` — number of pages to retrieve (default: 5)
- `save_as_page` — optional: save the answer as a new wiki page

**Flow:**
1. Hybrid search: BM25 + vector → RRF fusion → top-k wiki pages
2. Read full content of top-k pages
3. LLM call → synthesize answer with citations to wiki pages
4. If `save_as_page`: write answer as new wiki page, update index

**Output:** Answer text + list of cited wiki pages + relevance scores.

---

### 3. `lint`

**Purpose:** Health-check the wiki.

**Input:**
- `scope` — "all" or list of specific page paths
- `checks` — which checks to run (default: all)

**Checks:**
- Orphan pages (no inbound links)
- Broken links (reference nonexistent pages)
- Stale pages (source updated since last wiki compile)
- Missing pages (entities mentioned but no dedicated page)
- Duplicate entities (same concept split across pages)
- Contradiction detection (LLM-assisted: claims on page A vs page B)

**Output:** Report with issues grouped by severity + suggested fixes.

---

### 4. `list_sources`

**Input:** Optional filter by date, type, tag.
**Output:** Table of all files in `raw/` with metadata (date ingested, pages generated).

### 5. `list_pages`

**Input:** Optional filter by type (entity/concept/summary), tag, link count.
**Output:** Table of all wiki pages with metadata (type, source count, inbound links, last updated).

### 6. `update_schema`

**Input:** New schema text or patch instructions.
**Output:** Updated `schema.md`. Validates that the schema is parseable.

---

## Indexing pipeline

### BM25 (keyword search)

- **Engine:** SQLite FTS5 — zero dependencies, battle-tested, supports phrase queries
- **Indexed fields:** page title, body text, tags, entity names
- **Tokenizer:** unicode61 with remove_diacritics
- **Storage:** `.indexes/fts.db`

### Vector search (semantic)

- **Embedding model:** `all-MiniLM-L6-v2` (default, 384d, fast) — configurable to `nomic-embed-text` or any sentence-transformers model
- **Index:** FAISS IndexFlatIP (small scale) or IndexIVFFlat (>10K pages)
- **Granularity:** one embedding per wiki page (not per chunk — pages are already semantic units)
- **Storage:** `.indexes/vectors.faiss` + `.indexes/vectors_meta.json`

### Hybrid fusion

- **Method:** Reciprocal Rank Fusion (RRF) with k=60
- BM25 results and vector results merged via: `score = Σ 1/(k + rank_i)`
- Original query gets 2x weight over expanded variants
- Top-30 candidates passed to optional LLM re-ranker

### Index lifecycle

- Indexes are rebuilt incrementally on each ingest (only changed pages)
- Full rebuild available via CLI flag: `--rebuild-index`
- Indexes stored in `.indexes/` — gitignored, regenerable

---

## Wiki page format

Every wiki page is a markdown file with YAML frontmatter:

```markdown
---
title: "Transformer Architecture"
type: concept                    # entity | concept | summary | comparison | analysis
tags: [machine-learning, nlp]
sources: [raw/attention-paper.pdf, raw/bert-blog.md]
related: [attention-mechanism, positional-encoding, bert]
created: 2026-04-11
updated: 2026-04-11
---

# Transformer architecture

The transformer is a neural network architecture based on self-attention...

## Key components

...

## See also

- [[attention-mechanism]]
- [[positional-encoding]]
```

### Page types

| Type | Purpose | Example |
|------|---------|---------|
| entity | A specific thing (person, org, model, tool) | `openai.md`, `gpt-4.md` |
| concept | An idea or technique | `attention-mechanism.md` |
| summary | Summary of a single source | `summary--attention-paper.md` |
| comparison | Side-by-side analysis | `compare--bert-vs-gpt.md` |
| analysis | Synthesized answer saved from a query | `analysis--scaling-laws.md` |

---

## Configuration

Via environment variables or `.env` file, validated by Pydantic Settings:

```
WIKI_WORKSPACE=./workspace          # Root directory
WIKI_EMBEDDING_MODEL=all-MiniLM-L6-v2
WIKI_LLM_PROVIDER=anthropic         # anthropic | openai | ollama
WIKI_LLM_MODEL=claude-sonnet-4-20250514
WIKI_LLM_API_KEY=sk-...
WIKI_BM25_WEIGHT=0.5                # Weight in RRF fusion
WIKI_VECTOR_WEIGHT=0.5
WIKI_TOP_K=5                        # Default retrieval count
WIKI_MCP_TRANSPORT=stdio            # stdio | sse
WIKI_MCP_PORT=8181                  # Port for SSE transport
```

---

## Key design decisions

### 1. LLM calls: server-side vs client-side

**Decision: server-side.** The server calls the LLM API directly during ingest and query. This keeps the MCP tool interface clean — the client just calls `ingest(path)` and gets back results. The alternative (returning raw pages and letting the client synthesize) would work but pushes complexity to every client.

### 2. Atomic file writes

All wiki writes go through `writer.py` which writes to a temp file then renames. This prevents partial writes if the process crashes mid-ingest. The index.md update is the last step — if it fails, the pages exist but aren't cataloged (recoverable via lint).

### 3. One embedding per page, not per chunk

Traditional RAG chunks documents into 500-token fragments and embeds each. We don't need this because wiki pages are already semantically coherent units created by the LLM. A page about "attention mechanism" is a single concept — embedding it whole gives better retrieval than splitting it into arbitrary pieces.

If a page grows very long (>2000 tokens), the writer should prompt the LLM to split it into sub-pages instead.

### 4. Wikilinks as the graph

Cross-references use `[[page-name]]` syntax (Obsidian-compatible). `linker.py` maintains a backlink index so we can find all pages that reference a given entity. This graph is used by lint (orphan detection) and could power graph-based retrieval later.

### 5. Schema.md as the system prompt

The schema file is read by the server and injected into every LLM call. It tells the LLM how to structure pages, what naming conventions to follow, and what types of entities to extract. This is the "co-evolved" part — the user refines it over time.

---

## Error handling

| Failure | Recovery |
|---------|----------|
| LLM API call fails mid-ingest | Source is in `raw/`, no wiki pages written yet. Retry safe. |
| Process crashes during wiki write | Atomic writes via temp+rename. Partial pages don't exist. |
| Index out of sync with wiki | `lint` detects this. `--rebuild-index` fixes it. |
| Contradictory claims across pages | `lint --check contradictions` uses LLM to detect and flag. |
| Embedding model changed | Must rebuild vector index (`--rebuild-index`). BM25 unaffected. |

---

## Scaling limits

This design targets **personal to small-team use** (up to ~500 sources, ~1000 wiki pages).

Beyond that:
- SQLite FTS5 handles millions of rows, so BM25 scales fine
- FAISS IndexIVFFlat scales to ~100K vectors
- The bottleneck is LLM ingestion cost and wiki consistency
- For enterprise scale: replace filesystem with a database, add concurrency control, consider a knowledge graph backend

---

## Dependencies

```
# Core
fastapi
uvicorn
pydantic
pydantic-settings

# MCP
mcp                            # MCP Python SDK

# Indexing
faiss-cpu                      # Vector index
sentence-transformers          # Local embeddings

# Extraction
pymupdf                        # PDF text extraction
markdownify                    # HTML → markdown
python-frontmatter             # YAML frontmatter parsing

# LLM
anthropic                      # or openai, depending on provider

# Dev
pytest
httpx                          # For testing FastAPI
```

---

## MVP build order

1. **`config.py` + `server.py`** — FastAPI app with MCP stdio transport, workspace initialization
2. **`wiki/reader.py` + `wiki/writer.py`** — Read/write markdown with frontmatter
3. **`tools/ingest.py`** — Minimal: reads a file, calls LLM, writes summary page + updates index.md
4. **`indexing/bm25.py`** — SQLite FTS5 index over wiki pages
5. **`tools/query.py`** — BM25 search → return matching pages (no LLM synthesis yet)
6. **`indexing/embeddings.py` + `indexing/hybrid.py`** — Add vector search + RRF fusion
7. **`wiki/linker.py`** — Wikilink resolution + backlink tracking
8. **`tools/lint.py`** — Orphans, broken links, stale pages
9. **SSE transport** — For remote/web clients
10. **LLM-powered query synthesis** — Answer questions using retrieved pages as context