from unittest.mock import MagicMock, patch

import anthropic
import pytest

from wiki_llm.exceptions import LLMError
from wiki_llm.llm.client import ExtractedItem, IngestResponse, LLMClient


def _make_mock_client(parsed: IngestResponse) -> MagicMock:
    """Build a mock anthropic.Anthropic whose messages.parse() returns parsed."""
    mock_response = MagicMock()
    mock_response.parsed_output = parsed

    mock_messages = MagicMock()
    mock_messages.parse.return_value = mock_response

    mock_client = MagicMock(spec=anthropic.Anthropic)
    mock_client.messages = mock_messages
    return mock_client


SCHEMA = "## Wiki conventions\nUse slug names."
INDEX = "| Attention | attention.md | concept | nlp |"
TEXT = "Transformers use self-attention."


def test_extract_returns_ingest_response():
    expected = IngestResponse(
        summary="A doc about transformers.",
        entities=[ExtractedItem(name="transformer", type="concept", description="...")],
        concepts=[],
        claims=["Transformers use self-attention"],
    )
    client = LLMClient(_client=_make_mock_client(expected))
    result = client.extract(TEXT, SCHEMA, INDEX)
    assert result is expected


def test_extract_passes_schema_as_system_with_cache_control():
    expected = IngestResponse(summary="s", entities=[], concepts=[], claims=[])
    mock_client = _make_mock_client(expected)
    client = LLMClient(_client=mock_client)
    client.extract(TEXT, SCHEMA, INDEX)

    call_kwargs = mock_client.messages.parse.call_args.kwargs
    system = call_kwargs["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert SCHEMA in system[0]["text"]


def test_extract_includes_index_and_text_in_user_message():
    expected = IngestResponse(summary="s", entities=[], concepts=[], claims=[])
    mock_client = _make_mock_client(expected)
    client = LLMClient(_client=mock_client)
    client.extract(TEXT, SCHEMA, INDEX)

    call_kwargs = mock_client.messages.parse.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert INDEX in user_content
    assert TEXT in user_content


def test_extract_passes_ingest_response_as_output_format():
    expected = IngestResponse(summary="s", entities=[], concepts=[], claims=[])
    mock_client = _make_mock_client(expected)
    client = LLMClient(_client=mock_client)
    client.extract(TEXT, SCHEMA, INDEX)

    call_kwargs = mock_client.messages.parse.call_args.kwargs
    assert call_kwargs["output_format"] is IngestResponse


def test_api_error_raises_llm_error():
    mock_client = MagicMock(spec=anthropic.Anthropic)
    mock_client.messages = MagicMock()
    mock_client.messages.parse.side_effect = anthropic.APIStatusError(
        "API error", response=MagicMock(status_code=500), body={}
    )
    client = LLMClient(_client=mock_client)
    with pytest.raises(LLMError):
        client.extract(TEXT, SCHEMA, INDEX)


def test_llm_error_is_wiki_error():
    from wiki_llm.exceptions import WikiError
    assert issubclass(LLMError, WikiError)
