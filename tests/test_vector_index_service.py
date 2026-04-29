from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mindwiki.application.vector_index_service import VectorIndexService, build_chunk_embedding_text
from mindwiki.infrastructure.vector_index_repository import (
    ChunkEmbeddingMetadataUpdate,
    ChunkEmbeddingSource,
)
from mindwiki.infrastructure.milvus_store import MilvusChunkRecord
from mindwiki.llm.embedding_models import EmbeddingResponse, EmbeddingVector


class RecordingVectorIndexRepository:
    def __init__(self, chunks: tuple[ChunkEmbeddingSource, ...]) -> None:
        self._chunks = chunks
        self.updates: tuple[ChunkEmbeddingMetadataUpdate, ...] = ()

    def list_document_chunks_for_embedding(self, document_id: UUID) -> tuple[ChunkEmbeddingSource, ...]:
        return self._chunks

    def update_chunk_embedding_metadata(
        self,
        updates: tuple[ChunkEmbeddingMetadataUpdate, ...],
    ) -> None:
        self.updates = updates


class RecordingEmbeddingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def generate_embeddings(self, payload) -> EmbeddingResponse:
        self.calls.append(payload.texts)
        return EmbeddingResponse(
            model="Qwen/Qwen3-Embedding-8B",
            provider="openai_compatible",
            vectors=(
                EmbeddingVector(index=0, vector=(0.1, 0.2, 0.3)),
                EmbeddingVector(index=1, vector=(0.4, 0.5, 0.6)),
            ),
        )


class RecordingMilvusStore:
    def __init__(self) -> None:
        self.collection_dimensions: list[int] = []
        self.deleted_document_ids: list[str] = []
        self.records: tuple[MilvusChunkRecord, ...] = ()

    def ensure_collection(self, dimension: int) -> str:
        self.collection_dimensions.append(dimension)
        return "mindwiki_chunks"

    def delete_document_vectors(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)

    def upsert_chunk_vectors(self, records: tuple[MilvusChunkRecord, ...]) -> None:
        self.records = records


def build_chunk(chunk_id: str, section_title: str | None, chunk_text: str) -> ChunkEmbeddingSource:
    return ChunkEmbeddingSource(
        chunk_id=UUID(chunk_id),
        document_id=UUID("00000000-0000-0000-0000-000000000099"),
        section_id=UUID("00000000-0000-0000-0000-000000000055"),
        document_title="MindWiki Notes",
        section_title=section_title,
        chunk_text=chunk_text,
        source_type="markdown",
        document_type="markdown",
        document_tags=("rag", "vector"),
        imported_at=datetime(2026, 4, 29, 10, 0, 0),
    )


def test_build_chunk_embedding_text_skips_empty_section_title() -> None:
    chunk = build_chunk(
        "00000000-0000-0000-0000-000000000001",
        None,
        "Chunk body.",
    )

    assert build_chunk_embedding_text(chunk) == "Document Title: MindWiki Notes\nContent:\nChunk body."


def test_vector_index_service_syncs_embeddings_into_milvus_and_postgres() -> None:
    chunks = (
        build_chunk("00000000-0000-0000-0000-000000000001", "Overview", "Chunk A"),
        build_chunk("00000000-0000-0000-0000-000000000002", None, "Chunk B"),
    )
    repository = RecordingVectorIndexRepository(chunks)
    embedding_service = RecordingEmbeddingService()
    milvus_store = RecordingMilvusStore()
    service = VectorIndexService(repository, embedding_service, milvus_store)

    result = service.index_document(UUID("00000000-0000-0000-0000-000000000099"))

    assert result.chunk_count == 2
    assert result.embedding_model == "Qwen/Qwen3-Embedding-8B"
    assert result.embedding_dim == 3
    assert milvus_store.collection_dimensions == [3]
    assert milvus_store.deleted_document_ids == ["00000000-0000-0000-0000-000000000099"]
    assert len(milvus_store.records) == 2
    assert embedding_service.calls[0][0].startswith("Document Title: MindWiki Notes\nSection Title: Overview\nContent:\n")
    assert embedding_service.calls[0][1] == "Document Title: MindWiki Notes\nContent:\nChunk B"
    assert repository.updates[0].embedding_ref == "00000000-0000-0000-0000-000000000001"
    assert repository.updates[0].embedding_version == "v1"

