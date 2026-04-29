"""Minimal OpenAI-compatible chat completions provider."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Protocol
from urllib import error, request

from mindwiki.llm.models import (
    LLMError,
    LLMRequest,
    LLMResponse,
    LLMValidation,
    ResponseTiming,
    ValidationIssue,
    ValidationResult,
)
from mindwiki.llm.embedding_models import EmbeddingRequest, EmbeddingResponse, EmbeddingVector


class UrlopenCallable(Protocol):
    """Callable signature compatible with urllib.request.urlopen."""

    def __call__(self, req: request.Request, timeout: int): ...


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    """Runtime settings for one OpenAI-compatible provider."""

    base_url: str
    api_key: str
    default_model: str = ""


class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible `/chat/completions` endpoints."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        urlopen: UrlopenCallable | None = None,
    ) -> None:
        self._config = config
        self._urlopen = urlopen if urlopen is not None else request.urlopen

    def build_payload(self, llm_request: LLMRequest) -> dict[str, Any]:
        """Convert a unified request into an OpenAI-compatible payload."""

        model = llm_request.model or self._config.default_model
        return {
            "model": model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in llm_request.messages
            ],
            "temperature": llm_request.temperature,
            "top_p": llm_request.top_p,
            "max_tokens": llm_request.max_tokens,
            "stream": llm_request.stream,
            "response_format": llm_request.response_format,
        }

    def generate(self, llm_request: LLMRequest) -> LLMResponse:
        """Perform one provider call and normalize the result."""

        payload = self.build_payload(llm_request)
        body = json.dumps(payload).encode("utf-8")
        endpoint = self._build_endpoint()
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        started_at = time.monotonic()
        try:
            with self._urlopen(http_request, timeout=llm_request.timeout_ms / 1000) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            return self._build_http_error_response(llm_request, exc, started_at)
        except error.URLError as exc:
            return self._build_network_error_response(llm_request, exc, started_at)

        return self._build_success_response(llm_request, raw_response, started_at)

    def _build_endpoint(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        return f"{base_url}/chat/completions"

    def _build_success_response(
        self,
        llm_request: LLMRequest,
        raw_response: dict[str, Any],
        started_at: float,
    ) -> LLMResponse:
        choice = self._extract_first_choice(raw_response)
        content = ""
        finish_reason = ""
        protocol_validation = ValidationResult(passed=True)

        if choice is None:
            protocol_validation = ValidationResult(
                passed=False,
                issues=(
                    ValidationIssue(
                        code="missing_choice",
                        path="$.choices[0]",
                        message="Provider response does not include a usable first choice.",
                    ),
                ),
            )
        else:
            message = choice.get("message", {})
            content = message.get("content") or ""
            finish_reason = choice.get("finish_reason") or ""
            if not content:
                protocol_validation = ValidationResult(
                    passed=False,
                    issues=(
                        ValidationIssue(
                            code="empty_message_content",
                            path="$.choices[0].message.content",
                            message="Provider response content is empty.",
                        ),
                    ),
                )

        validation = LLMValidation(
            protocol_validation=protocol_validation,
            final_status="accepted" if protocol_validation.passed else "rejected",
        )
        status = "success" if protocol_validation.passed else "failed"
        response_error = None
        if not protocol_validation.passed:
            response_error = LLMError(
                error_type="protocol_validation_failed",
                retryable=False,
                fallback_allowed=llm_request.retry_policy.allow_fallback,
                message=protocol_validation.issues[0].message,
            )

        usage = raw_response.get("usage", {})
        return LLMResponse(
            request_id=str(llm_request.metadata.get("request_id", "")),
            model=raw_response.get("model") or llm_request.model,
            output_text=content,
            status=status,
            validation=validation,
            timing=ResponseTiming(latency_ms=self._latency_ms(started_at)),
            error=response_error,
            provider_response_id=raw_response.get("id", ""),
            finish_reason=finish_reason,
            usage=self._normalize_usage(usage),
            raw_response=raw_response,
        )

    def _build_http_error_response(
        self,
        llm_request: LLMRequest,
        exc: error.HTTPError,
        started_at: float,
    ) -> LLMResponse:
        status_code = exc.code
        retryable = status_code >= 500 or status_code == 429
        fallback_allowed = retryable and llm_request.retry_policy.allow_fallback
        return LLMResponse(
            request_id=str(llm_request.metadata.get("request_id", "")),
            model=llm_request.model,
            output_text="",
            status="failed",
            validation=LLMValidation(final_status="rejected"),
            timing=ResponseTiming(latency_ms=self._latency_ms(started_at)),
            error=LLMError(
                error_type="http_error",
                retryable=retryable,
                fallback_allowed=fallback_allowed,
                message=f"HTTP {status_code}: {exc.reason}",
            ),
        )

    def _build_network_error_response(
        self,
        llm_request: LLMRequest,
        exc: error.URLError,
        started_at: float,
    ) -> LLMResponse:
        return LLMResponse(
            request_id=str(llm_request.metadata.get("request_id", "")),
            model=llm_request.model,
            output_text="",
            status="failed",
            validation=LLMValidation(final_status="rejected"),
            timing=ResponseTiming(latency_ms=self._latency_ms(started_at)),
            error=LLMError(
                error_type="network_error",
                retryable=True,
                fallback_allowed=llm_request.retry_policy.allow_fallback,
                message=str(exc.reason),
            ),
        )

    @staticmethod
    def _extract_first_choice(raw_response: dict[str, Any]) -> dict[str, Any] | None:
        choices = raw_response.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        return first_choice if isinstance(first_choice, dict) else None

    @staticmethod
    def _normalize_usage(usage: dict[str, Any]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                normalized[key] = value
        return normalized

    @staticmethod
    def _latency_ms(started_at: float) -> int:
        return int((time.monotonic() - started_at) * 1000)


class OpenAICompatibleEmbeddingProvider:
    """Adapter for OpenAI-compatible `/embeddings` endpoints."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        urlopen: UrlopenCallable | None = None,
    ) -> None:
        self._config = config
        self._urlopen = urlopen if urlopen is not None else request.urlopen

    def build_payload(self, embedding_request: EmbeddingRequest) -> dict[str, Any]:
        model = embedding_request.model or self._config.default_model
        return {
            "model": model,
            "input": list(embedding_request.texts),
            "encoding_format": "float",
        }

    def embed(self, embedding_request: EmbeddingRequest) -> EmbeddingResponse:
        payload = self.build_payload(embedding_request)
        body = json.dumps(payload).encode("utf-8")
        endpoint = self._build_endpoint()
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with self._urlopen(http_request, timeout=embedding_request.timeout_ms / 1000) as response:
            raw_response = json.loads(response.read().decode("utf-8"))

        data = raw_response.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError("Embedding provider response does not include data.")

        vectors: list[EmbeddingVector] = []
        for item in data:
            if not isinstance(item, dict):
                raise RuntimeError("Embedding provider returned an invalid item.")
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise RuntimeError("Embedding provider returned an empty embedding vector.")
            index = int(item.get("index", len(vectors)))
            vectors.append(
                EmbeddingVector(
                    index=index,
                    vector=tuple(float(value) for value in vector),
                )
            )

        vectors.sort(key=lambda item: item.index)
        usage = raw_response.get("usage", {})
        normalized_usage: dict[str, int] = {}
        for key in ("prompt_tokens", "total_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                normalized_usage[key] = value

        return EmbeddingResponse(
            model=str(raw_response.get("model") or embedding_request.model),
            vectors=tuple(vectors),
            provider="openai_compatible",
            usage=normalized_usage,
        )

    def _build_endpoint(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        return f"{base_url}/embeddings"
