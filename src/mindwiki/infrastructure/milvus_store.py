"""Milvus-backed chunk vector storage helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from pymilvus import DataType, MilvusClient

from mindwiki.infrastructure.settings import get_settings


@dataclass(frozen=True, slots=True)
class MilvusChunkRecord:
    """One chunk vector record stored in Milvus."""

    id: str
    chunk_id: str
    document_id: str
    section_id: str | None
    source_type: str
    document_type: str
    document_tags: tuple[str, ...]
    imported_at_epoch_ms: int | None
    embedding_version: str
    vector: tuple[float, ...]
    is_active: bool = True


class MilvusStore(Protocol):
    """Store contract for chunk vector writes."""

    def ensure_collection(self, dimension: int) -> str: ...

    def delete_document_vectors(self, document_id: str) -> None: ...

    def upsert_chunk_vectors(self, records: tuple[MilvusChunkRecord, ...]) -> None: ...


class MilvusChunkStore:
    """Milvus-backed store for chunk vectors."""

    def __init__(self, uri: str, *, token: str = "", collection_name: str = "mindwiki_chunks") -> None:
        self._uri = uri
        self._token = token
        self._collection_name = collection_name
        self._client: MilvusClient | None = None

    def ensure_collection(self, dimension: int) -> str:
        client = self._get_client()
        if client.has_collection(self._collection_name):
            return self._collection_name

        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=64)
        schema.add_field("document_id", DataType.VARCHAR, max_length=64)
        schema.add_field("section_id", DataType.VARCHAR, max_length=64, nullable=True)
        schema.add_field("source_type", DataType.VARCHAR, max_length=32)
        schema.add_field("document_type", DataType.VARCHAR, max_length=32)
        schema.add_field("document_tags", DataType.JSON)
        schema.add_field("imported_at_epoch_ms", DataType.INT64, nullable=True)
        schema.add_field("embedding_version", DataType.VARCHAR, max_length=32)
        schema.add_field("is_active", DataType.BOOL)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dimension)

        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            metric_type="COSINE",
            index_type="AUTOINDEX",
        )

        client.create_collection(
            collection_name=self._collection_name,
            schema=schema,
            index_params=index_params,
        )
        return self._collection_name

    def delete_document_vectors(self, document_id: str) -> None:
        client = self._get_client()
        if not client.has_collection(self._collection_name):
            return
        client.delete(
            self._collection_name,
            filter=f'document_id == "{document_id}"',
        )

    def upsert_chunk_vectors(self, records: tuple[MilvusChunkRecord, ...]) -> None:
        if not records:
            return

        dimension = len(records[0].vector)
        self.ensure_collection(dimension)
        payload = [
            {
                "id": record.id,
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "section_id": record.section_id,
                "source_type": record.source_type,
                "document_type": record.document_type,
                "document_tags": list(record.document_tags),
                "imported_at_epoch_ms": record.imported_at_epoch_ms,
                "embedding_version": record.embedding_version,
                "is_active": record.is_active,
                "vector": list(record.vector),
            }
            for record in records
        ]
        self._get_client().upsert(self._collection_name, payload)

    def _get_client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(
                uri=self._uri,
                token=self._token,
            )
        return self._client


def datetime_to_epoch_ms(value: datetime | None) -> int | None:
    """Convert a datetime to epoch milliseconds."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def build_milvus_store() -> MilvusStore | None:
    """Build the default Milvus store if configuration is present."""

    settings = get_settings()
    if not settings.milvus_uri:
        return None
    return MilvusChunkStore(
        settings.milvus_uri,
        token=settings.milvus_token,
        collection_name=settings.milvus_collection_name,
    )
