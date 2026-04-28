"""Service entrypoints for minimal LLM generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from mindwiki.infrastructure.settings import get_settings
from mindwiki.llm.models import LLMMessage, LLMRequest, LLMResponse, RetryPolicy
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)


class TextGenerationProvider(Protocol):
    """Provider interface used by the minimal text generation service."""

    def generate(self, llm_request: LLMRequest) -> LLMResponse: ...


@dataclass(frozen=True, slots=True)
class GenerateTextInput:
    """Minimal input shape for the first generation entrypoint."""

    system_prompt: str
    user_prompt: str
    task_type: str = "generate_text"
    model: str = ""
    temperature: float = 0.2
    top_p: float = 1.0
    max_tokens: int = 1024
    response_format: dict | None = None
    timeout_ms: int | None = None
    max_retries: int = 0
    allow_fallback: bool = False
    metadata: dict[str, object] | None = None


class LLMService:
    """Minimal service wrapper for the first `generate_text` capability."""

    def __init__(self, provider: TextGenerationProvider) -> None:
        self._provider = provider

    def generate_text(self, payload: GenerateTextInput) -> LLMResponse:
        request_id = self._resolve_request_id(payload.metadata)
        metadata = dict(payload.metadata or {})
        metadata.setdefault("request_id", request_id)
        metadata.setdefault("interface_name", "generate_text")

        llm_request = LLMRequest(
            task_type=payload.task_type,
            model=payload.model,
            messages=(
                LLMMessage(role="system", content=payload.system_prompt),
                LLMMessage(role="user", content=payload.user_prompt),
            ),
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            response_format=payload.response_format,
            timeout_ms=self._resolve_timeout_ms(payload.timeout_ms),
            retry_policy=RetryPolicy(
                max_retries=payload.max_retries,
                allow_fallback=payload.allow_fallback,
            ),
            metadata=metadata,
        )
        return self._provider.generate(llm_request)

    @staticmethod
    def _resolve_request_id(metadata: dict[str, object] | None) -> str:
        if metadata is not None and "request_id" in metadata and metadata["request_id"]:
            return str(metadata["request_id"])
        return str(uuid4())

    @staticmethod
    def _resolve_timeout_ms(timeout_ms: int | None) -> int:
        if timeout_ms is not None:
            return timeout_ms
        return get_settings().llm_timeout_ms


def build_llm_service() -> LLMService:
    """Build the default LLM service from environment-backed settings."""

    settings = get_settings()
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            default_model=settings.llm_model_id,
        )
    )
    return LLMService(provider)
