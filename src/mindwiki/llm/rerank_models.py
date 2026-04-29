"""Core request/response models for rerank integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RerankDocument:
    """One candidate document passed into a rerank request."""

    document_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RerankRequest:
    """Unified rerank request shape for first-stage orchestration."""

    query: str
    documents: tuple[RerankDocument, ...]
    model: str
    top_n: int = 5
    timeout_ms: int = 30000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RerankResult:
    """One normalized rerank result item."""

    index: int
    document_id: str
    relevance_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RerankResponse:
    """Unified rerank response shape."""

    model: str
    results: tuple[RerankResult, ...]
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: dict[str, Any] | None = None
