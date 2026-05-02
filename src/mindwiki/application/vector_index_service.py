"""Application service for chunk embedding generation and Milvus sync."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from mindwiki.infrastructure.vector_index_repository import (
    ChunkEmbeddingMetadataUpdate,
    ChunkEmbeddingSource,
    VectorIndexRepository,
    build_vector_index_repository,
)
from mindwiki.observability.logger import ensure_request_id
from mindwiki.infrastructure.milvus_store import (
    MilvusChunkRecord,
    MilvusStore,
    build_milvus_store,
    datetime_to_epoch_ms,
)
from mindwiki.llm.embedding_service import (
    EmbeddingService,
    GenerateEmbeddingsInput,
    build_embedding_service,
)


EMBEDDING_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class DocumentVectorSyncResult:
    """Summary for one document vector sync."""

    document_id: UUID
    chunk_count: int
    embedding_model: str
    embedding_dim: int
    collection_name: str


class VectorIndexService:
    """Generate chunk embeddings and sync them into Milvus."""

    def __init__(
        self,
        repository: VectorIndexRepository,
        embedding_service: EmbeddingService,
        milvus_store: MilvusStore,
    ) -> None:
        self._repository = repository
        self._embedding_service = embedding_service
        self._milvus_store = milvus_store

    def index_document(
        self,
        document_id: UUID,
        *,
        request_id: str | None = None,
    ) -> DocumentVectorSyncResult:
        chunks = self._repository.list_document_chunks_for_embedding(document_id)
        if not chunks:
            raise RuntimeError(f"No active chunks found for document {document_id}.")

        resolved_request_id = ensure_request_id(
            None if request_id is None else {"request_id": request_id}
        )
        texts = tuple(build_chunk_embedding_text(chunk) for chunk in chunks)
        embedding_response = self._embedding_service.generate_embeddings(
            GenerateEmbeddingsInput(
                texts=texts,
                metadata={
                    "request_id": resolved_request_id,
                    "document_id": str(document_id),
                    "embedding_version": EMBEDDING_VERSION,
                },
            )
        )
        if len(embedding_response.vectors) != len(chunks):
            raise RuntimeError("Embedding count does not match chunk count.")

        embedding_dim = len(embedding_response.vectors[0].vector)
        collection_name = self._milvus_store.ensure_collection(embedding_dim)
        self._milvus_store.delete_document_vectors(str(document_id))

        records: list[MilvusChunkRecord] = []
        updates: list[ChunkEmbeddingMetadataUpdate] = []
        for chunk, vector in zip(chunks, embedding_response.vectors, strict=True):
            embedding_ref = str(chunk.chunk_id)
            records.append(
                MilvusChunkRecord(
                    id=embedding_ref,
                    chunk_id=str(chunk.chunk_id),
                    document_id=str(chunk.document_id),
                    section_id=str(chunk.section_id) if chunk.section_id is not None else None,
                    source_type=chunk.source_type,
                    document_type=chunk.document_type,
                    document_tags=chunk.document_tags,
                    imported_at_epoch_ms=datetime_to_epoch_ms(chunk.imported_at),
                    embedding_version=EMBEDDING_VERSION,
                    vector=vector.vector,
                )
            )
            updates.append(
                ChunkEmbeddingMetadataUpdate(
                    chunk_id=chunk.chunk_id,
                    embedding_ref=embedding_ref,
                    embedding_provider=embedding_response.provider,
                    embedding_model=embedding_response.model,
                    embedding_version=EMBEDDING_VERSION,
                    embedding_dim=embedding_dim,
                )
            )

        self._milvus_store.upsert_chunk_vectors(tuple(records))
        self._repository.update_chunk_embedding_metadata(tuple(updates))
        return DocumentVectorSyncResult(
            document_id=document_id,
            chunk_count=len(chunks),
            embedding_model=embedding_response.model,
            embedding_dim=embedding_dim,
            collection_name=collection_name,
        )


def build_chunk_embedding_text(chunk: ChunkEmbeddingSource) -> str:
    """Build the first-stage embedding input for one chunk."""

    lines = [f"Document Title: {chunk.document_title}"]
    if chunk.section_title:
        lines.append(f"Section Title: {chunk.section_title}")
    lines.extend(
        [
            "Content:",
            chunk.chunk_text,
        ]
    )
    return "\n".join(lines)


def build_vector_index_service() -> VectorIndexService | None:
    """Build the default vector index service if dependencies are configured."""

    repository = build_vector_index_repository()
    embedding_service = build_embedding_service()
    milvus_store = build_milvus_store()
    if repository is None or embedding_service is None or milvus_store is None:
        return None
    return VectorIndexService(repository, embedding_service, milvus_store)
