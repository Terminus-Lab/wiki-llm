from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel

from wiki_llm.exceptions import LLMError

PageType = Literal["entity", "concept", "summary", "comparison", "analysis"]

_SYSTEM_SUFFIX = """
You extract structured knowledge from documents and return it as structured JSON.
For each entity (person, org, model, tool) and concept (idea, technique) found,
produce a dedicated entry with a slug-style name (lowercase, hyphens).
"""


class ExtractedItem(BaseModel):
    name: str
    type: PageType
    description: str
    related: list[str] = []
    tags: list[str] = []


class IngestResponse(BaseModel):
    summary: str
    entities: list[ExtractedItem] = []
    concepts: list[ExtractedItem] = []
    claims: list[str] = []


class LLMClient:
    """Thin wrapper around the Anthropic SDK for wiki ingestion calls."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str = "",
        _client: anthropic.Anthropic | None = None,
    ) -> None:
        self._model = model
        # Accept a pre-built client for testing (dependency injection)
        self._client = _client or anthropic.Anthropic(api_key=api_key or None)

    def extract(self, text: str, schema_text: str, index_text: str) -> IngestResponse:
        """Call the LLM to extract structured knowledge from source text.

        Args:
            text:        Extracted plain text of the source document.
            schema_text: Contents of schema.md — injected as system prompt.
                         Cached with prompt caching (stable across calls).
            index_text:  Contents of index.md — existing pages the LLM should
                         be aware of to avoid duplicating entries.
        """
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": schema_text + _SYSTEM_SUFFIX,
                        # Cache the schema — it's identical on every ingest call
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Current wiki index:\n{index_text}\n\n"
                            f"Source document:\n{text}"
                        ),
                    }
                ],
                output_format=IngestResponse,
            )
            return response.parsed_output
        except anthropic.APIError as exc:
            raise LLMError(str(exc)) from exc
