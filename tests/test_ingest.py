from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from wiki_llm.config import Settings
from wiki_llm.exceptions import PageNotFound
from wiki_llm.llm.client import ExtractedItem, IngestResponse, LLMClient
from wiki_llm.tools.ingest import IngestResult, run_ingest
from wiki_llm.wiki.reader import read_page

DIM = 8


class MockEncoder:
    def get_sentence_embedding_dimension(self) -> int:
        return DIM

    def encode(self, sentences: list[str], normalize_embeddings: bool = True) -> np.ndarray:
        vecs = []
        for text in sentences:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            v = rng.random(DIM).astype(np.float32)
            if normalize_embeddings:
                v /= np.linalg.norm(v)
            vecs.append(v)
        return np.array(vecs, dtype=np.float32)


def _mock_llm(response: IngestResponse) -> LLMClient:
    mock = MagicMock(spec=LLMClient)
    mock.extract.return_value = response
    return mock


def _cfg(tmp_path: Path) -> Settings:
    return Settings(workspace=str(tmp_path / "workspace"))


def _source(tmp_path: Path, name: str = "paper.txt", content: str = "Hello world.") -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


RESPONSE = IngestResponse(
    summary="A paper about transformers.",
    entities=[
        ExtractedItem(name="transformer", type="concept", description="A neural network using self-attention.", tags=["nlp"], related=["attention"]),
    ],
    concepts=[
        ExtractedItem(name="attention", type="concept", description="Focuses on relevant parts of input.", tags=["nlp"], related=[]),
    ],
    claims=["Transformers outperform RNNs on sequence tasks."],
)


# --- basic happy path ---

def test_ingest_copies_source_to_raw(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    result = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert result.raw_path.exists()
    assert result.raw_path.parent == cfg.raw_dir


def test_ingest_creates_entity_pages(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    result = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert any(p.name == "transformer.md" for p in result.created)


def test_ingest_creates_concept_pages(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    result = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert any(p.name == "attention.md" for p in result.created)


def test_ingest_creates_summary_page(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    result = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert any("summary--" in p.name for p in result.created)


def test_ingest_result_has_summary_text(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    result = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert "transformer" in result.summary.lower()


def test_ingest_updates_catalog(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert cfg.index_md.exists()
    assert "transformer" in cfg.index_md.read_text().lower()


def test_ingest_appends_log(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert cfg.log_md.exists()
    assert "paper.txt" in cfg.log_md.read_text()


def test_ingest_populates_bm25_index(tmp_path):
    from wiki_llm.indexing.bm25 import BM25Index
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    with BM25Index(cfg.indexes_dir / "fts.db") as bm25:
        assert bm25.count() > 0


# --- update existing page ---

def test_ingest_updates_existing_page(tmp_path):
    cfg = _cfg(tmp_path)
    src1 = _source(tmp_path, "paper1.txt", "First paper.")
    src2 = _source(tmp_path, "paper2.txt", "Second paper.")

    run_ingest(src1, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    result2 = run_ingest(src2, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())

    # "transformer" page already existed — should be in updated, not created
    assert any(p.name == "transformer.md" for p in result2.updated)
    assert not any(p.name == "transformer.md" for p in result2.created)


def test_updated_page_has_both_sources(tmp_path):
    cfg = _cfg(tmp_path)
    src1 = _source(tmp_path, "paper1.txt", "First paper.")
    src2 = _source(tmp_path, "paper2.txt", "Second paper.")

    run_ingest(src1, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    run_ingest(src2, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())

    page = read_page(cfg.wiki_dir / "transformer.md")
    assert len(page.sources) == 2


# --- error handling ---

def test_missing_source_raises_page_not_found(tmp_path):
    cfg = _cfg(tmp_path)
    with pytest.raises(PageNotFound):
        run_ingest(tmp_path / "ghost.txt", cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())


def test_duplicate_raw_file_renamed(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path, "doc.txt")
    r1 = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    r2 = run_ingest(src, cfg=cfg, _llm_client=_mock_llm(RESPONSE), _embedding_model=MockEncoder())
    assert r1.raw_path != r2.raw_path


# --- guidance is forwarded ---

def test_guidance_passed_to_llm(tmp_path):
    cfg = _cfg(tmp_path)
    src = _source(tmp_path)
    mock = _mock_llm(RESPONSE)
    run_ingest(src, "focus on methodology", cfg=cfg, _llm_client=mock, _embedding_model=MockEncoder())
    call_kwargs = mock.extract.call_args
    assert "focus on methodology" in call_kwargs.args or "focus on methodology" in str(call_kwargs.kwargs)
