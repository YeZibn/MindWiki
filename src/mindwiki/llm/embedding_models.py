"""Shared models for embedding generation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """One embedding generation request."""

    model: str
    texts: tuple[str, ...]
    timeout_ms: int = 30000
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """One generated embedding vector."""

    index: int
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Normalized embedding response."""

    model: str
    vectors: tuple[EmbeddingVector, ...]
    provider: str
    usage: dict[str, int] = field(default_factory=dict)

