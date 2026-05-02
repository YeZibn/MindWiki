"""Minimal structured application logging helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
from time import monotonic
from typing import Any
from uuid import uuid4

from mindwiki.infrastructure.settings import get_settings

_LEVEL_BY_NAME = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


@dataclass(frozen=True, slots=True)
class LogEvent:
    """Normalized structured log event."""

    event: str
    level: str = "INFO"
    request_id: str = ""
    interface_name: str = ""
    stage: str = ""
    status: str = ""
    duration_ms: int | None = None
    metadata: dict[str, Any] | None = None


class StructuredLogger:
    """Emit structured JSON lines to stdout/stderr and a local file."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._settings = get_settings()
        self._level = _resolve_level(self._settings.log_level)

    def emit(self, event: LogEvent) -> None:
        event_level = _resolve_level(event.level)
        if event_level < self._level:
            return

        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": event.level.upper(),
            "logger": self._name,
            "event": event.event,
            "request_id": event.request_id,
            "interface_name": event.interface_name,
            "stage": event.stage,
            "status": event.status,
            "duration_ms": event.duration_ms,
            "metadata": _sanitize_metadata(event.metadata or {}),
        }
        serialized = json.dumps(payload, ensure_ascii=False)
        stream = sys.stderr if event_level >= logging.ERROR else sys.stdout
        stream.write(serialized + "\n")
        stream.flush()
        _append_log_file(self._settings.log_file_path, serialized)


class LogTimer:
    """Simple monotonic timer for duration logging."""

    def __init__(self) -> None:
        self._started_at = monotonic()

    def elapsed_ms(self) -> int:
        return int((monotonic() - self._started_at) * 1000)


def get_logger(name: str) -> StructuredLogger:
    """Build a structured logger instance."""

    return StructuredLogger(name)


def ensure_request_id(metadata: dict[str, object] | None = None) -> str:
    """Resolve or generate a stable request id for the current flow."""

    if metadata is not None and metadata.get("request_id"):
        return str(metadata["request_id"])
    return str(uuid4())


def _resolve_level(level_name: str) -> int:
    return _LEVEL_BY_NAME.get(level_name.upper(), logging.INFO)


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered_key = key.lower()
        if "api_key" in lowered_key or "authorization" in lowered_key or "token" in lowered_key:
            sanitized[key] = "<redacted>"
            continue
        if isinstance(value, str) and len(value) > 500:
            sanitized[key] = f"{value[:500]}..."
            continue
        sanitized[key] = value
    return sanitized


def _append_log_file(log_file_path: str, serialized_payload: str) -> None:
    path = Path(log_file_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(serialized_payload + "\n")
