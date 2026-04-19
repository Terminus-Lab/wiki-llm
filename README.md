# wiki-llm

A local, file-based knowledge base powered by an LLM. You feed it documents (PDFs, markdown, plain text, HTML); it reads them, extracts entities and concepts, and writes structured, interlinked wiki pages — all stored as plain markdown on your filesystem.

Built on [Karpathy's LLM Wiki pattern](https://x.com/karpathy). Exposes an [MCP](https://modelcontextprotocol.io) server so Claude Code, Cursor, or any MCP client can call `ingest` and `query` directly.

---

## How it works

```
You                     wiki-llm MCP server
 │  ingest("paper.pdf") │
 │──────────────────────▶  1. Copy → raw/
 │                       │  2. Extract text (PDF/HTML/md/txt)
 │                       │  3. LLM call → entities, concepts, claims
 │                       │  4. Write wiki pages (atomic)
 │                       │  5. Update BM25 + vector indexes
 │                       │  6. Rebuild index.md + append log.md
 │◀──────────────────────│
 │  "Created: transformer.md, attention.md, summary--paper.md"
```

Workspace layout after a few ingests:

```
workspace/
  raw/              immutable copies of every source you've ingested
  wiki/             LLM-generated markdown pages
  index.md          auto-maintained page catalog
  log.md            append-only ingest history
  schema.md         wiki conventions (edit to steer the LLM)
  .indexes/         BM25 (SQLite FTS5) + vector (FAISS) — gitignored
```

---

## Requirements

- Python 3.11+
- An Anthropic API key (`ANTHROPIC_API_KEY` or `WIKI_LLM_API_KEY`)

---

## Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/Terminus-Lab/wiki-llm
cd wiki-llm

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Set your API key
export WIKI_LLM_API_KEY=sk-ant-...   # or add to a .env file
```

---

## Starting the server

### stdio (default — used by MCP clients like Claude Code)

```bash
python server.py
```

The server speaks the MCP protocol over stdin/stdout. It creates the workspace directories on first run.

### SSE (for remote or web clients)

```bash
WIKI_MCP_TRANSPORT=sse python server.py
# Listening on http://localhost:8181
```

### Connect from Claude Code

Add this to your Claude Code MCP config (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "wiki-llm": {
      "command": "python",
      "args": ["/absolute/path/to/wiki-llm/server.py"],
      "env": {
        "WIKI_LLM_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

---

## Ingesting documents

Once the server is running, call the `ingest` tool from your MCP client.

**From Claude Code (after connecting):**

```
ingest source_path="./papers/attention.pdf"
ingest source_path="./notes/ml-reading-list.md" guidance="focus on the model architectures"
```

**Programmatically (Python):**

```python
from wiki_llm.tools.ingest import run_ingest
from wiki_llm.config import Settings

cfg = Settings(workspace="./my-wiki")
result = run_ingest("attention.pdf", cfg=cfg)

print(result.created)   # [Path('wiki/transformer.md'), Path('wiki/attention.md'), ...]
print(result.summary)   # "A seminal paper introducing the Transformer architecture..."
```

Supported file types: `.pdf`, `.md`, `.txt`, `.csv`, `.json`, `.html`, `.htm`

---

## Configuration

Via environment variables or a `.env` file in the project root:

| Variable | Default | Description |
|---|---|---|
| `WIKI_WORKSPACE` | `./workspace` | Root directory for all wiki data |
| `WIKI_LLM_API_KEY` | — | Anthropic API key |
| `WIKI_LLM_MODEL` | `claude-sonnet-4-6` | Model used for extraction |
| `WIKI_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for vector search |
| `WIKI_TOP_K` | `5` | Default number of pages returned by search |
| `WIKI_MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `WIKI_MCP_PORT` | `8181` | Port for SSE transport |

---

## Running tests

```bash
pytest                        # all tests
pytest tests/test_ingest.py   # ingest flow only
pytest tests/test_bm25.py     # BM25 index only
```

Tests use mock LLM clients and mock encoders — no API key or model download needed.

---

## MCP tools

| Tool | Description |
|---|---|
| `ingest` | Process a source file → write wiki pages, update indexes |
| `list_pages` | Show the current page catalog (`index.md`) |
| `update_schema` | Replace `schema.md` (the conventions injected into every LLM call) |
