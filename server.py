"""MCP server entry point.

stdio (default):
    python server.py

SSE:
    WIKI_MCP_TRANSPORT=sse python server.py
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from wiki_llm.config import settings
from wiki_llm.tools.ingest import IngestResult, run_ingest

mcp = FastMCP(
    "wiki-llm",
    instructions=(
        "A personal knowledge base. "
        "Use `ingest` to add documents, `query` to search."
    ),
)

# ---------------------------------------------------------------------------
# Workspace bootstrap
# ---------------------------------------------------------------------------

def _init_workspace() -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.indexes_dir.mkdir(parents=True, exist_ok=True)
    if not settings.schema_md.exists():
        from wiki_llm.tools.ingest import _DEFAULT_SCHEMA
        settings.schema_md.write_text(_DEFAULT_SCHEMA)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(description="Ingest a source file into the wiki knowledge base.")
def ingest(
    source_path: str,
    guidance: str = "",
) -> str:
    """Process a raw source into structured wiki pages.

    Args:
        source_path: Path to the file to ingest (absolute or relative to cwd).
        guidance:    Optional hint for the LLM, e.g. "focus on the results section".
    """
    result: IngestResult = run_ingest(source_path, guidance)

    lines = [f"Ingested: {result.raw_path.name}"]
    if result.created:
        lines.append(f"Created ({len(result.created)}): " + ", ".join(p.name for p in result.created))
    if result.updated:
        lines.append(f"Updated ({len(result.updated)}): " + ", ".join(p.name for p in result.updated))
    lines.append(f"\nSummary: {result.summary}")
    return "\n".join(lines)


@mcp.tool(description="List all pages currently in the wiki.")
def list_pages() -> str:
    """Return a summary of all wiki pages."""
    from wiki_llm.wiki.catalog import read_catalog_text
    return read_catalog_text(settings.index_md)


@mcp.tool(description="Read or update the wiki schema (conventions injected into every LLM prompt).")
def update_schema(new_schema: str) -> str:
    """Replace the contents of schema.md.

    Args:
        new_schema: Full replacement text for the schema.
    """
    settings.schema_md.write_text(new_schema)
    return f"Schema updated ({len(new_schema)} chars)."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _init_workspace()
    transport = settings.mcp_transport
    if transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
