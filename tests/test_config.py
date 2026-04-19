import pytest
from pathlib import Path
from wiki_llm.config import Settings


def test_defaults():
    s = Settings()
    assert s.workspace == Path("./workspace")
    assert s.llm_provider == "anthropic"
    assert s.llm_model == "claude-sonnet-4-6"
    assert s.embedding_model == "all-MiniLM-L6-v2"
    assert s.top_k == 5
    assert s.bm25_weight == 0.5
    assert s.vector_weight == 0.5
    assert s.mcp_transport == "stdio"
    assert s.mcp_port == 8181


def test_derived_paths():
    s = Settings(workspace="/tmp/test-wiki")
    assert s.raw_dir == Path("/tmp/test-wiki/raw")
    assert s.wiki_dir == Path("/tmp/test-wiki/wiki")
    assert s.indexes_dir == Path("/tmp/test-wiki/.indexes")
    assert s.index_md == Path("/tmp/test-wiki/index.md")
    assert s.log_md == Path("/tmp/test-wiki/log.md")
    assert s.schema_md == Path("/tmp/test-wiki/schema.md")


def test_override_via_env(monkeypatch):
    monkeypatch.setenv("WIKI_WORKSPACE", "/tmp/override")
    monkeypatch.setenv("WIKI_TOP_K", "10")
    monkeypatch.setenv("WIKI_MCP_TRANSPORT", "sse")

    s = Settings()
    assert s.workspace == Path("/tmp/override")
    assert s.top_k == 10
    assert s.mcp_transport == "sse"


def test_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WIKI_WORKSPACE=/tmp/from-env-file\nWIKI_MCP_PORT=9090\n")

    s = Settings(_env_file=str(env_file))
    assert s.workspace == Path("/tmp/from-env-file")
    assert s.mcp_port == 9090
