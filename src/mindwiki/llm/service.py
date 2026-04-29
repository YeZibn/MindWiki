"""Service entrypoints for minimal LLM generation."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol
from uuid import uuid4

from mindwiki.infrastructure.settings import get_settings
from mindwiki.llm.models import (
    LLMError,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    ResponseTiming,
    RetryPolicy,
)
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
    overall_deadline_ms: int | None = None
    max_retries: int = 0
    allow_fallback: bool = False
    metadata: dict[str, object] | None = None


class LLMService:
    """Minimal service wrapper for the first `generate_text` capability."""

    def __init__(
        self,
        provider: TextGenerationProvider,
        *,
        fallback_provider: TextGenerationProvider | None = None,
    ) -> None:
        self._provider = provider
        self._fallback_provider = fallback_provider

    def generate_text(self, payload: GenerateTextInput) -> LLMResponse:
        request_id = self._resolve_request_id(payload.metadata)
        metadata = dict(payload.metadata or {})
        metadata.setdefault("request_id", request_id)
        metadata.setdefault("interface_name", "generate_text")
        request_timeout_ms = self._resolve_timeout_ms(payload.timeout_ms)
        overall_deadline_ms = self._resolve_overall_deadline_ms(
            payload.overall_deadline_ms,
            request_timeout_ms,
        )
        started_at = time.monotonic()

        response = self._run_with_retries(
            provider=self._provider,
            payload=payload,
            metadata=metadata,
            request_timeout_ms=request_timeout_ms,
            request_id=request_id,
            overall_deadline_ms=overall_deadline_ms,
            started_at=started_at,
        )
        if response.status == "success":
            return response

        if not self._should_use_fallback(response, payload.allow_fallback):
            return response

        if self._fallback_provider is None:
            return response

        fallback_model = get_settings().llm_model_mini_id
        if not fallback_model:
            return response

        fallback_payload = GenerateTextInput(
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            task_type=payload.task_type,
            model=fallback_model,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            response_format=payload.response_format,
            timeout_ms=request_timeout_ms,
            overall_deadline_ms=overall_deadline_ms,
            max_retries=0,
            allow_fallback=False,
            metadata=metadata,
        )
        return self._run_with_retries(
            provider=self._fallback_provider,
            payload=fallback_payload,
            metadata=metadata,
            request_timeout_ms=request_timeout_ms,
            request_id=request_id,
            overall_deadline_ms=overall_deadline_ms,
            started_at=started_at,
            is_fallback=True,
        )

    def _run_with_retries(
        self,
        *,
        provider: TextGenerationProvider,
        payload: GenerateTextInput,
        metadata: dict[str, object],
        request_timeout_ms: int,
        request_id: str,
        overall_deadline_ms: int,
        started_at: float,
        is_fallback: bool = False,
    ) -> LLMResponse:
        max_attempts = payload.max_retries + 1
        response: LLMResponse | None = None

        for attempt_index in range(max_attempts):
            elapsed_ms = self._elapsed_ms(started_at)
            if elapsed_ms >= overall_deadline_ms:
                return self._build_deadline_exceeded_response(
                    request_id=request_id,
                    model=payload.model,
                    elapsed_ms=elapsed_ms,
                    allow_fallback=payload.allow_fallback and not is_fallback,
                )

            attempt_metadata = dict(metadata)
            attempt_metadata["attempt_id"] = self._build_attempt_id(
                request_id=request_id,
                attempt_number=attempt_index + 1,
                is_fallback=is_fallback,
            )
            attempt_metadata["retry_count"] = attempt_index
            attempt_metadata["is_fallback"] = is_fallback

            llm_request = self._build_request(
                payload=payload,
                metadata=attempt_metadata,
                request_timeout_ms=request_timeout_ms,
            )
            response = provider.generate(llm_request)
            if response.status == "success":
                return response

            if response.error is None or not response.error.retryable:
                return response

            if attempt_index >= max_attempts - 1:
                return response

        return response if response is not None else self._build_deadline_exceeded_response(
            request_id=request_id,
            model=payload.model,
            elapsed_ms=self._elapsed_ms(started_at),
            allow_fallback=payload.allow_fallback and not is_fallback,
        )

    @staticmethod
    def _build_request(
        *,
        payload: GenerateTextInput,
        metadata: dict[str, object],
        request_timeout_ms: int,
    ) -> LLMRequest:
        return LLMRequest(
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
            timeout_ms=request_timeout_ms,
            retry_policy=RetryPolicy(
                max_retries=payload.max_retries,
                allow_fallback=payload.allow_fallback,
            ),
            metadata=metadata,
        )

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

    @staticmethod
    def _resolve_overall_deadline_ms(
        overall_deadline_ms: int | None,
        request_timeout_ms: int,
    ) -> int:
        if overall_deadline_ms is not None:
            return overall_deadline_ms
        return request_timeout_ms

    @staticmethod
    def _build_attempt_id(
        *,
        request_id: str,
        attempt_number: int,
        is_fallback: bool,
    ) -> str:
        attempt_prefix = "fallback" if is_fallback else "primary"
        return f"{request_id}:{attempt_prefix}:{attempt_number}"

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.monotonic() - started_at) * 1000)

    @staticmethod
    def _should_use_fallback(response: LLMResponse, allow_fallback: bool) -> bool:
        if not allow_fallback or response.error is None:
            return False
        return response.error.fallback_allowed

    @staticmethod
    def _build_deadline_exceeded_response(
        *,
        request_id: str,
        model: str,
        elapsed_ms: int,
        allow_fallback: bool,
    ) -> LLMResponse:
        return LLMResponse(
            request_id=request_id,
            model=model,
            output_text="",
            status="failed",
            error=LLMError(
                error_type="deadline_exceeded",
                retryable=False,
                fallback_allowed=allow_fallback,
                message=f"Overall deadline exceeded after {elapsed_ms} ms.",
            ),
            timing=ResponseTiming(latency_ms=elapsed_ms),
        )


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
    fallback_provider = None
    if settings.llm_model_mini_id:
        fallback_provider = OpenAICompatibleProvider(
            OpenAICompatibleConfig(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                default_model=settings.llm_model_mini_id,
            )
        )
    return LLMService(provider, fallback_provider=fallback_provider)
