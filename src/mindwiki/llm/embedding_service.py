"""Service entrypoints for minimal embedding generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mindwiki.infrastructure.settings import get_settings
from mindwiki.llm.embedding_models import EmbeddingRequest, EmbeddingResponse
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleEmbeddingProvider,
)


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

        settings = get_settings()
        model = payload.model or settings.llm_embedding_model_id
        if not model:
            raise RuntimeError("LLM_EMBEDDING_MODEL_ID is not configured.")

        timeout_ms = payload.timeout_ms or settings.llm_embedding_timeout_ms
        request = EmbeddingRequest(
            model=model,
            texts=payload.texts,
            timeout_ms=timeout_ms,
            metadata=dict(payload.metadata or {}),
        )
        return self._provider.embed(request)


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
