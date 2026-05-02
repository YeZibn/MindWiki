"""Service entrypoints for minimal LLM generation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Protocol

from mindwiki.infrastructure.settings import get_settings
from mindwiki.llm.models import (
    LLMError,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMValidation,
    ResponseTiming,
    RetryPolicy,
    ValidationIssue,
    ValidationResult,
)
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from mindwiki.observability.logger import LogEvent, LogTimer, ensure_request_id, get_logger

_LOGGER = get_logger("mindwiki.llm")


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
        request_id = ensure_request_id(payload.metadata)
        metadata = dict(payload.metadata or {})
        metadata.setdefault("request_id", request_id)
        metadata.setdefault("interface_name", "generate_text")
        request_timeout_ms = self._resolve_timeout_ms(payload.timeout_ms)
        overall_deadline_ms = self._resolve_overall_deadline_ms(
            payload.overall_deadline_ms,
            request_timeout_ms,
        )
        timer = LogTimer()
        started_at = time.monotonic()
        _LOGGER.emit(
            LogEvent(
                event="llm_generate_text_started",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "generate_text")),
                stage="llm_generate_text",
                status="started",
                metadata={
                    "task_type": payload.task_type,
                    "model": payload.model or get_settings().llm_model_id,
                    "max_tokens": payload.max_tokens,
                    "allow_fallback": payload.allow_fallback,
                },
            )
        )

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
            _LOGGER.emit(
                LogEvent(
                    event="llm_generate_text_completed",
                    request_id=request_id,
                    interface_name=str(metadata.get("interface_name", "generate_text")),
                    stage="llm_generate_text",
                    status="success",
                    duration_ms=timer.elapsed_ms(),
                    metadata={
                        "task_type": payload.task_type,
                        "model": response.model,
                        "finish_reason": response.finish_reason,
                        "validation_status": response.validation.final_status,
                    },
                )
            )
            return response

        if not self._should_use_fallback(response, payload.allow_fallback):
            _LOGGER.emit(
                LogEvent(
                    event="llm_generate_text_completed",
                    request_id=request_id,
                    interface_name=str(metadata.get("interface_name", "generate_text")),
                    stage="llm_generate_text",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={
                        "task_type": payload.task_type,
                        "model": response.model,
                        "error_type": "" if response.error is None else response.error.error_type,
                    },
                )
            )
            return response

        if self._fallback_provider is None:
            _LOGGER.emit(
                LogEvent(
                    event="llm_generate_text_completed",
                    request_id=request_id,
                    interface_name=str(metadata.get("interface_name", "generate_text")),
                    stage="llm_generate_text",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={
                        "task_type": payload.task_type,
                        "model": response.model,
                        "error_type": "" if response.error is None else response.error.error_type,
                        "fallback_provider": "missing",
                    },
                )
            )
            return response

        fallback_model = get_settings().llm_model_mini_id
        if not fallback_model:
            _LOGGER.emit(
                LogEvent(
                    event="llm_generate_text_completed",
                    request_id=request_id,
                    interface_name=str(metadata.get("interface_name", "generate_text")),
                    stage="llm_generate_text",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={
                        "task_type": payload.task_type,
                        "model": response.model,
                        "error_type": "" if response.error is None else response.error.error_type,
                        "fallback_model": "missing",
                    },
                )
            )
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
        fallback_response = self._run_with_retries(
            provider=self._fallback_provider,
            payload=fallback_payload,
            metadata=metadata,
            request_timeout_ms=request_timeout_ms,
            request_id=request_id,
            overall_deadline_ms=overall_deadline_ms,
            started_at=started_at,
            is_fallback=True,
        )
        _LOGGER.emit(
            LogEvent(
                event="llm_generate_text_completed",
                request_id=request_id,
                interface_name=str(metadata.get("interface_name", "generate_text")),
                stage="llm_generate_text",
                status=fallback_response.status,
                duration_ms=timer.elapsed_ms(),
                metadata={
                    "task_type": payload.task_type,
                    "model": fallback_response.model,
                    "used_fallback": True,
                    "validation_status": fallback_response.validation.final_status,
                    "error_type": "" if fallback_response.error is None else fallback_response.error.error_type,
                },
            )
        )
        return fallback_response

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
            response = self._finalize_response(
                provider.generate(llm_request),
                payload=payload,
                allow_fallback=payload.allow_fallback and not is_fallback,
            )
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

    @staticmethod
    def _finalize_response(
        response: LLMResponse,
        *,
        payload: GenerateTextInput,
        allow_fallback: bool,
    ) -> LLMResponse:
        if response.status != "success":
            return response

        if not payload.response_format:
            return response

        if payload.response_format.get("type") != "json_schema":
            return response

        parse_result = LLMService._parse_structured_output(response.output_text)
        if parse_result["error"] is not None:
            issue = ValidationIssue(
                code="json_decode_failed",
                path="$",
                message=str(parse_result["error"]),
            )
            return LLMService._build_schema_failure_response(
                response=response,
                issues=(issue,),
                final_status="repairable",
                allow_fallback=allow_fallback,
            )

        parsed_output = parse_result["value"]
        schema = payload.response_format.get("json_schema", {}).get("schema", {})
        issues = tuple(
            LLMService._validate_against_schema(
                value=parsed_output,
                schema=schema,
                path="$",
            )
        )
        if issues:
            return LLMService._build_schema_failure_response(
                response=response,
                issues=issues,
                final_status="repairable",
                allow_fallback=allow_fallback,
                parsed_output=parsed_output,
            )

        return LLMResponse(
            request_id=response.request_id,
            model=response.model,
            output_text=response.output_text,
            status="success",
            parsed_output=parsed_output,
            validation=LLMValidation(
                protocol_validation=response.validation.protocol_validation,
                schema_validation=ValidationResult(passed=True),
                citation_validation=response.validation.citation_validation,
                final_status="accepted",
            ),
            timing=response.timing,
            error=None,
            provider_response_id=response.provider_response_id,
            finish_reason=response.finish_reason,
            usage=response.usage,
            raw_response=response.raw_response,
        )

    @staticmethod
    def _build_schema_failure_response(
        *,
        response: LLMResponse,
        issues: tuple[ValidationIssue, ...],
        final_status: str,
        allow_fallback: bool,
        parsed_output: Any | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            request_id=response.request_id,
            model=response.model,
            output_text=response.output_text,
            status="failed",
            parsed_output=parsed_output,
            validation=LLMValidation(
                protocol_validation=response.validation.protocol_validation,
                schema_validation=ValidationResult(
                    passed=False,
                    issues=issues,
                ),
                citation_validation=response.validation.citation_validation,
                final_status=final_status,
            ),
            timing=response.timing,
            error=LLMError(
                error_type="schema_validation_failed",
                retryable=False,
                fallback_allowed=allow_fallback,
                message=issues[0].message if issues else "Schema validation failed.",
            ),
            provider_response_id=response.provider_response_id,
            finish_reason=response.finish_reason,
            usage=response.usage,
            raw_response=response.raw_response,
        )

    @staticmethod
    def _parse_structured_output(output_text: str) -> dict[str, Any]:
        candidates = [output_text.strip()]
        stripped = output_text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                candidates.append("\n".join(lines[1:-1]).strip())

        for candidate in candidates:
            try:
                return {"value": json.loads(candidate), "error": None}
            except json.JSONDecodeError as exc:
                last_error = exc

        return {"value": None, "error": last_error}

    @staticmethod
    def _validate_against_schema(
        *,
        value: Any,
        schema: dict[str, Any],
        path: str,
    ) -> list[ValidationIssue]:
        if not schema:
            return []

        issues: list[ValidationIssue] = []
        expected_type = schema.get("type")
        if expected_type is not None and not LLMService._value_matches_type(value, expected_type):
            issues.append(
                ValidationIssue(
                    code="type_mismatch",
                    path=path,
                    message=f"Expected {expected_type} at {path}.",
                )
            )
            return issues

        if expected_type == "object":
            if not isinstance(value, dict):
                return issues

            required_fields = schema.get("required", [])
            for field_name in required_fields:
                if field_name not in value:
                    issues.append(
                        ValidationIssue(
                            code="missing_required_field",
                            path=f"{path}.{field_name}",
                            message=f"Missing required field: {field_name}.",
                        )
                    )

            properties = schema.get("properties", {})
            for field_name, field_schema in properties.items():
                if field_name not in value:
                    continue
                issues.extend(
                    LLMService._validate_against_schema(
                        value=value[field_name],
                        schema=field_schema,
                        path=f"{path}.{field_name}",
                    )
                )

        if expected_type == "array":
            if not isinstance(value, list):
                return issues

            item_schema = schema.get("items", {})
            for index, item in enumerate(value):
                issues.extend(
                    LLMService._validate_against_schema(
                        value=item,
                        schema=item_schema,
                        path=f"{path}[{index}]",
                    )
                )

        return issues

    @staticmethod
    def _value_matches_type(value: Any, expected_type: str) -> bool:
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        return True


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
