from __future__ import annotations

import json
from pathlib import Path

from mindwiki.observability.logger import LogEvent, ensure_request_id, get_logger
from mindwiki.infrastructure import settings as settings_module


def test_ensure_request_id_generates_when_missing() -> None:
    request_id = ensure_request_id()

    assert request_id
    assert isinstance(request_id, str)


def test_ensure_request_id_reuses_existing_metadata_value() -> None:
    request_id = ensure_request_id({"request_id": "req_123"})

    assert request_id == "req_123"


def test_structured_logger_emits_json_line_and_redacts_sensitive_fields(capsys) -> None:
    logger = get_logger("mindwiki.test")

    logger.emit(
        LogEvent(
            event="test_event",
            level="INFO",
            request_id="req_001",
            interface_name="test_interface",
            stage="test_stage",
            status="success",
            duration_ms=12,
            metadata={
                "api_key": "secret",
                "token_value": "secret-token",
                "normal": "value",
            },
        )
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["event"] == "test_event"
    assert payload["request_id"] == "req_001"
    assert payload["interface_name"] == "test_interface"
    assert payload["stage"] == "test_stage"
    assert payload["status"] == "success"
    assert payload["duration_ms"] == 12
    assert payload["metadata"]["api_key"] == "<redacted>"
    assert payload["metadata"]["token_value"] == "<redacted>"
    assert payload["metadata"]["normal"] == "value"


def test_structured_logger_also_appends_to_local_log_file(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    log_path = tmp_path / "logs" / "mindwiki.jsonl"
    env_path.write_text(
        (
            "LOG_LEVEL=INFO\n"
            "LOG_FORMAT=json\n"
            f"LOG_FILE_PATH={log_path}\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LOG_FILE_PATH", raising=False)
    monkeypatch.setattr(settings_module, "DOTENV_PATH", env_path)
    settings_module.clear_settings_cache()

    logger = get_logger("mindwiki.test.file")
    logger.emit(
        LogEvent(
            event="file_event",
            request_id="req_file_001",
            interface_name="file_test",
            stage="file_stage",
            status="success",
            metadata={"normal": "value"},
        )
    )

    capsys.readouterr()
    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "file_event"
    assert payload["request_id"] == "req_file_001"
    assert payload["metadata"]["normal"] == "value"

    settings_module.clear_settings_cache()
