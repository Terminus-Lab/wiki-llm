from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WIKI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Workspace
    workspace: Path = Path("./workspace")

    # LLM
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    llm_api_key: str = ""

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Retrieval
    top_k: int = 5
    bm25_weight: float = 0.5
    vector_weight: float = 0.5

    # MCP transport
    mcp_transport: str = "stdio"
    mcp_port: int = 8181

    # Derived paths
    @property
    def raw_dir(self) -> Path:
        return self.workspace / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.workspace / "wiki"

    @property
    def indexes_dir(self) -> Path:
        return self.workspace / ".indexes"

    @property
    def index_md(self) -> Path:
        return self.workspace / "index.md"

    @property
    def log_md(self) -> Path:
        return self.workspace / "log.md"

    @property
    def schema_md(self) -> Path:
        return self.workspace / "schema.md"


settings = Settings()
