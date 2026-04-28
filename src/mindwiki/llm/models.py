"""Core request/response models for LLM integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A single chat-completions style message."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Minimal retry and fallback controls for one request."""

    max_retries: int = 0
    allow_fallback: bool = False


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation issue discovered after a model call."""

    code: str
    path: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation outcome for one validation layer."""

    passed: bool = True
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMValidation:
    """Structured validation summary for one LLM response."""

    protocol_validation: ValidationResult = field(default_factory=ValidationResult)
    schema_validation: ValidationResult = field(default_factory=ValidationResult)
    citation_validation: ValidationResult = field(default_factory=ValidationResult)
    final_status: str = "accepted"


@dataclass(frozen=True, slots=True)
class ResponseTiming:
    """Timing details for one completed model call."""

    latency_ms: int = 0


@dataclass(frozen=True, slots=True)
class LLMError:
    """Normalized LLM call error information."""

    error_type: str
    retryable: bool
    fallback_allowed: bool
    message: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Unified LLM request shape for the first integration stage."""

    task_type: str
    model: str
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.2
    top_p: float = 1.0
    max_tokens: int = 1024
    response_format: dict[str, Any] | None = None
    stream: bool = False
    timeout_ms: int = 30000
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Unified LLM response shape for the first integration stage."""

    request_id: str
    model: str
    output_text: str
    status: str
    parsed_output: dict[str, Any] | None = None
    validation: LLMValidation = field(default_factory=LLMValidation)
    timing: ResponseTiming = field(default_factory=ResponseTiming)
    error: LLMError | None = None
    provider_response_id: str = ""
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: dict[str, Any] | None = None
