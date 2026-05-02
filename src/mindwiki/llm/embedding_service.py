"""Service entrypoints for minimal embedding generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mindwiki.infrastructure.settings import get_settings
from mindwiki.observability.logger import LogEvent, LogTimer, ensure_request_id, get_logger
from mindwiki.llm.embedding_models import EmbeddingRequest, EmbeddingResponse
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleEmbeddingProvider,
)

_LOGGER = get_logger("mindwiki.embedding")


class EmbeddingProvider(Protocol):
    """Provider interface for embedding generation."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


@dataclass(frozen=True, slots=True)
class GenerateEmbeddingsInput:
    """Minimal input shape for the first embedding entrypoint."""

    texts: tuple[str, ...]
    model: str = ""
    timeout_ms: int | None = None
    metadata: dict[str, object] | None = None


class EmbeddingService:
    """Minimal service wrapper for embedding generation."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def generate_embeddings(self, payload: GenerateEmbeddingsInput) -> EmbeddingResponse:
        if not payload.texts:
            raise ValueError("Embedding input texts must not be empty.")

        request_id = ensure_request_id(payload.metadata)
        settings = get_settings()
        model = payload.model or settings.llm_embedding_model_id
        if not model:
            raise RuntimeError("LLM_EMBEDDING_MODEL_ID is not configured.")

        timeout_ms = payload.timeout_ms or settings.llm_embedding_timeout_ms
        timer = LogTimer()
        metadata = dict(payload.metadata or {})
        metadata.setdefault("request_id", request_id)
        metadata.setdefault("interface_name", "embedding")
        _LOGGER.emit(
            LogEvent(
                event="embedding_started",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "embedding")),
                stage="embedding",
                status="started",
                metadata={
                    "model": model,
                    "text_count": len(payload.texts),
                },
            )
        )
        request = EmbeddingRequest(
            model=model,
            texts=payload.texts,
            timeout_ms=timeout_ms,
            metadata=metadata,
        )
        response = self._provider.embed(request)
        _LOGGER.emit(
            LogEvent(
                event="embedding_completed",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "embedding")),
                stage="embedding",
                status="success",
                duration_ms=timer.elapsed_ms(),
                metadata={
                    "model": response.model,
                    "provider": response.provider,
                    "vector_count": len(response.vectors),
                },
            )
        )
        return response


def build_embedding_service() -> EmbeddingService | None:
    """Build the default embedding service if configuration is present."""

    settings = get_settings()
    if not settings.llm_embedding_base_url or not settings.llm_embedding_api_key:
        return None

    provider = OpenAICompatibleEmbeddingProvider(
        OpenAICompatibleConfig(
            base_url=settings.llm_embedding_base_url,
            api_key=settings.llm_embedding_api_key,
            default_model=settings.llm_embedding_model_id,
        )
    )
    return EmbeddingService(provider)
