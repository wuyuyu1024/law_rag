from pathlib import Path

from tax_rag.common import DEFAULT_CONFIG, expand_chunks_for_stress
from tax_rag.indexing import ensure_local_qdrant_index, qdrant_vector_params
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import ChunkRecord, SecurityClassification, SourceType


def _chunk(
    *,
    chunk_id: str,
    source_type: SourceType,
    text: str,
    citation_path: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
    article: str | None = None,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text=text,
        citation_path=citation_path,
        source_type=source_type,
        jurisdiction="NL",
        allowed_roles=allowed_roles,
        source_path=f"fixtures/{chunk_id}.xml",
        article=article,
        security_classification=security_classification,
    )


def test_persistent_local_qdrant_index_is_built_and_reused(tmp_path: Path) -> None:
    chunk = _chunk(
        chunk_id="law-home-office",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    index_path = tmp_path / "qdrant"

    build_result = ensure_local_qdrant_index([chunk], path=str(index_path), recreate=True)

    assert build_result["created"] is True
    assert build_result["point_count"] == 1

    service = RetrievalService(
        chunks=[chunk],
        default_method=RetrievalMethod.DENSE,
        dense_index_path=str(index_path),
    )

    response_a = service.retrieve("deductibility of home office expenses", "helpdesk")
    response_b = service.retrieve("deductibility of home office expenses", "helpdesk")

    assert response_a.results[0].chunk_id == "law-home-office"
    assert response_a.metadata["vector_backend"] == "qdrant_local_persistent"
    assert response_b.metadata["vector_backend"] == "qdrant_local_persistent"
    assert response_b.results[0].chunk_id == "law-home-office"


def test_expand_chunks_for_stress_creates_distinct_replicas() -> None:
    chunk = _chunk(
        chunk_id="law-home-office",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )

    expanded = expand_chunks_for_stress([chunk], multiplier=3)

    assert len(expanded) == 3
    assert expanded[0].chunk_id.endswith("::stress:1")
    assert expanded[1].chunk_id.endswith("::stress:2")
    assert expanded[2].metadata["synthetic_stress"] is True


def test_qdrant_vector_params_use_configured_ann_and_quantization_settings() -> None:
    params = qdrant_vector_params(256)

    assert params.hnsw_config is not None
    assert params.hnsw_config.m == DEFAULT_CONFIG.retrieval.qdrant_hnsw_m
    assert params.hnsw_config.ef_construct == DEFAULT_CONFIG.retrieval.qdrant_ef_construct
    assert params.quantization_config is not None
    assert params.on_disk == DEFAULT_CONFIG.retrieval.qdrant_on_disk_vectors
