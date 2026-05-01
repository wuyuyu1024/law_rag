"""Persistent local Qdrant index helpers for dense retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings

from qdrant_client import QdrantClient, models

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.common.dense import dense_text, embed_text, payload_for_chunk
from tax_rag.schemas import ChunkRecord

DEFAULT_DENSE_COLLECTION_NAME = "dense_chunks"

_PAYLOAD_INDEX_FIELDS: tuple[tuple[str, models.PayloadSchemaType], ...] = (
    ("allowed_roles", models.PayloadSchemaType.KEYWORD),
    ("source_type", models.PayloadSchemaType.KEYWORD),
    ("jurisdiction", models.PayloadSchemaType.KEYWORD),
    ("security_classification", models.PayloadSchemaType.KEYWORD),
    ("security_classification_rank", models.PayloadSchemaType.INTEGER),
    ("valid_from", models.PayloadSchemaType.DATETIME),
    ("valid_to", models.PayloadSchemaType.DATETIME),
    ("article", models.PayloadSchemaType.KEYWORD),
    ("ecli", models.PayloadSchemaType.KEYWORD),
)


def qdrant_payload_index_fields() -> tuple[str, ...]:
    return tuple(field_name for field_name, _field_schema in _PAYLOAD_INDEX_FIELDS)


def qdrant_vector_params(dimensions: int) -> models.VectorParams:
    quantization_config = None
    if DEFAULT_CONFIG.retrieval.qdrant_scalar_quantization:
        quantization_config = models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                quantile=DEFAULT_CONFIG.retrieval.qdrant_scalar_quantile,
                always_ram=DEFAULT_CONFIG.retrieval.qdrant_quantization_always_ram,
            )
        )
    return models.VectorParams(
        size=dimensions,
        distance=models.Distance.COSINE,
        hnsw_config=models.HnswConfigDiff(
            m=DEFAULT_CONFIG.retrieval.qdrant_hnsw_m,
            ef_construct=DEFAULT_CONFIG.retrieval.qdrant_ef_construct,
        ),
        quantization_config=quantization_config,
        on_disk=DEFAULT_CONFIG.retrieval.qdrant_on_disk_vectors,
    )


@dataclass(frozen=True)
class LocalQdrantIndex:
    path: str
    collection_name: str = DEFAULT_DENSE_COLLECTION_NAME
    dimensions: int = DEFAULT_CONFIG.retrieval.dense_dimensions

    def client(self) -> QdrantClient:
        return QdrantClient(path=self.path)

    def ensure_collection(
        self,
        chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
        *,
        recreate: bool = False,
    ) -> dict[str, object]:
        path = Path(self.path)
        path.mkdir(parents=True, exist_ok=True)
        client = self.client()

        if recreate and client.collection_exists(self.collection_name):
            client.delete_collection(self.collection_name)

        created = False
        if not client.collection_exists(self.collection_name):
            created = True
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_vector_params(self.dimensions),
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                for field_name, field_schema in _PAYLOAD_INDEX_FIELDS:
                    client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_schema,
                    )
            if chunks:
                client.upload_collection(
                    collection_name=self.collection_name,
                    ids=list(range(1, len(chunks) + 1)),
                    vectors=[embed_text(dense_text(chunk), dimensions=self.dimensions) for chunk in chunks],
                    payload=[payload_for_chunk(chunk) for chunk in chunks],
                )

        point_count = client.count(self.collection_name, exact=True).count
        return {
            "path": self.path,
            "collection_name": self.collection_name,
            "created": created,
            "point_count": int(point_count),
            "payload_index_fields": qdrant_payload_index_fields(),
        }


def ensure_local_qdrant_index(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    *,
    path: str,
    collection_name: str = DEFAULT_DENSE_COLLECTION_NAME,
    dimensions: int = DEFAULT_CONFIG.retrieval.dense_dimensions,
    recreate: bool = False,
) -> dict[str, object]:
    index = LocalQdrantIndex(path=path, collection_name=collection_name, dimensions=dimensions)
    return index.ensure_collection(chunks, recreate=recreate)
