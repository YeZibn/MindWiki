"""Service entrypoints for minimal rerank execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mindwiki.infrastructure.settings import get_settings
from mindwiki.observability.logger import LogEvent, LogTimer, ensure_request_id, get_logger
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleRerankProvider,
)
from mindwiki.llm.rerank_models import RerankDocument, RerankRequest, RerankResponse

_LOGGER = get_logger("mindwiki.rerank")


class RerankProvider(Protocol):
    """Provider interface for rerank execution."""

    def rerank(self, request: RerankRequest) -> RerankResponse: ...


@dataclass(frozen=True, slots=True)
class RerankInput:
    """Minimal input shape for rerank execution."""

    query: str
    documents: tuple[RerankDocument, ...]
    model: str = ""
    top_n: int = 5
    timeout_ms: int | None = None
    metadata: dict[str, object] | None = None


class RerankService:
    """Minimal service wrapper for first-stage rerank execution."""

    def __init__(self, provider: RerankProvider) -> None:
        self._provider = provider

    def rerank(self, payload: RerankInput) -> RerankResponse:
        if not payload.documents:
            raise ValueError("Rerank input documents must not be empty.")

        request_id = ensure_request_id(payload.metadata)
        settings = get_settings()
        model = payload.model or settings.llm_rerank_model_id
        if not model:
            raise RuntimeError("LLM_RERANK_MODEL_ID is not configured.")

        timeout_ms = payload.timeout_ms or settings.llm_rerank_timeout_ms
        timer = LogTimer()
        metadata = dict(payload.metadata or {})
        metadata.setdefault("request_id", request_id)
        metadata.setdefault("interface_name", "rerank")
        _LOGGER.emit(
            LogEvent(
                event="rerank_started",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "rerank")),
                stage="rerank",
                status="started",
                metadata={
                    "model": model,
                    "document_count": len(payload.documents),
                    "top_n": payload.top_n,
                },
            )
        )
        request = RerankRequest(
            query=payload.query,
            documents=payload.documents,
            model=model,
            top_n=payload.top_n,
            timeout_ms=timeout_ms,
            metadata=metadata,
        )
        response = self._provider.rerank(request)
        _LOGGER.emit(
            LogEvent(
                event="rerank_completed",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "rerank")),
                stage="rerank",
                status="success",
                duration_ms=timer.elapsed_ms(),
                metadata={
                    "model": response.model,
                    "result_count": len(response.results),
                },
            )
        )
        return response


def build_rerank_service() -> RerankService | None:
    """Build the default rerank service if configuration is present."""

    settings = get_settings()
    if not settings.llm_rerank_base_url or not settings.llm_rerank_api_key:
        return None

    provider = OpenAICompatibleRerankProvider(
        OpenAICompatibleConfig(
            base_url=settings.llm_rerank_base_url,
            api_key=settings.llm_rerank_api_key,
            default_model=settings.llm_rerank_model_id,
        )
    )
    return RerankService(provider)
