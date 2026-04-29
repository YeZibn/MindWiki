from __future__ import annotations

from pathlib import Path

from mindwiki.infrastructure import settings as settings_module
from mindwiki.llm.models import LLMError, LLMResponse, LLMValidation, ResponseTiming
from mindwiki.llm.service import GenerateTextInput, LLMService, build_llm_service


class RecordingProvider:
    def __init__(self) -> None:
        self.last_request = None
        self.requests = []

    def generate(self, llm_request):
        self.last_request = llm_request
        self.requests.append(llm_request)
        return LLMResponse(
            request_id=str(llm_request.metadata.get("request_id", "")),
            model=llm_request.model or "gpt-5.4",
            output_text="done",
            status="success",
            validation=LLMValidation(final_status="accepted"),
            timing=ResponseTiming(latency_ms=5),
        )


class SequencedProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self.requests = []

    def generate(self, llm_request):
        self.requests.append(llm_request)
        return self._responses.pop(0)


def test_generate_text_builds_llm_request_for_provider() -> None:
    provider = RecordingProvider()
    service = LLMService(provider)

    response = service.generate_text(
        GenerateTextInput(
            system_prompt="Follow the schema.",
            user_prompt="Question and evidence.",
            task_type="qa",
            model="gpt-5.4",
            temperature=0.1,
            max_tokens=512,
            max_retries=2,
            allow_fallback=True,
            metadata={"trace_id": "trace_001"},
        )
    )

    assert response.status == "success"
    assert provider.last_request is not None
    assert provider.last_request.task_type == "qa"
    assert provider.last_request.model == "gpt-5.4"
    assert provider.last_request.messages[0].role == "system"
    assert provider.last_request.messages[1].content == "Question and evidence."
    assert provider.last_request.retry_policy.max_retries == 2
    assert provider.last_request.retry_policy.allow_fallback is True
    assert provider.last_request.metadata["interface_name"] == "generate_text"
    assert provider.last_request.metadata["trace_id"] == "trace_001"
    assert provider.last_request.metadata["request_id"]
    assert provider.last_request.metadata["attempt_id"].endswith(":primary:1")
    assert provider.last_request.metadata["retry_count"] == 0
    assert provider.last_request.metadata["is_fallback"] is False


def test_generate_text_uses_settings_timeout_when_not_overridden(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        (
            "LLM_BASE_URL=https://kuaipao.ai/v1\n"
            "LLM_API_KEY=test-key\n"
            "LLM_MODEL_ID=gpt-5.4\n"
            "LLM_TIMEOUT_MS=45000\n"
        ),
        encoding="utf-8",
    )
    provider = RecordingProvider()

    monkeypatch.setattr(settings_module, "DOTENV_PATH", env_path)
    settings_module.clear_settings_cache()

    service = LLMService(provider)
    service.generate_text(
        GenerateTextInput(
            system_prompt="Follow the schema.",
            user_prompt="Question and evidence.",
        )
    )

    assert provider.last_request is not None
    assert provider.last_request.timeout_ms == 45000

    settings_module.clear_settings_cache()


def test_generate_text_retries_retryable_primary_failures() -> None:
    provider = SequencedProvider(
        [
            LLMResponse(
                request_id="req_001",
                model="gpt-5.4",
                output_text="",
                status="failed",
                error=LLMError(
                    error_type="network_error",
                    retryable=True,
                    fallback_allowed=True,
                    message="temporary",
                ),
            ),
            LLMResponse(
                request_id="req_001",
                model="gpt-5.4",
                output_text="done",
                status="success",
                validation=LLMValidation(final_status="accepted"),
                timing=ResponseTiming(latency_ms=5),
            ),
        ]
    )
    service = LLMService(provider)

    response = service.generate_text(
        GenerateTextInput(
            system_prompt="Follow the schema.",
            user_prompt="Question and evidence.",
            model="gpt-5.4",
            max_retries=1,
            metadata={"request_id": "req_001"},
        )
    )

    assert response.status == "success"
    assert len(provider.requests) == 2
    assert provider.requests[0].metadata["attempt_id"] == "req_001:primary:1"
    assert provider.requests[1].metadata["attempt_id"] == "req_001:primary:2"
    assert provider.requests[1].metadata["retry_count"] == 1


def test_generate_text_uses_fallback_provider_after_primary_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        (
            "LLM_MODEL_MINI_ID=gpt-5.4-mini\n"
            "LLM_TIMEOUT_MS=45000\n"
        ),
        encoding="utf-8",
    )
    primary_provider = SequencedProvider(
        [
            LLMResponse(
                request_id="req_001",
                model="gpt-5.4",
                output_text="",
                status="failed",
                error=LLMError(
                    error_type="http_error",
                    retryable=True,
                    fallback_allowed=True,
                    message="upstream failure",
                ),
            ),
        ]
    )
    fallback_provider = RecordingProvider()

    monkeypatch.setattr(settings_module, "DOTENV_PATH", env_path)
    settings_module.clear_settings_cache()

    service = LLMService(primary_provider, fallback_provider=fallback_provider)
    response = service.generate_text(
        GenerateTextInput(
            system_prompt="Follow the schema.",
            user_prompt="Question and evidence.",
            model="gpt-5.4",
            allow_fallback=True,
            metadata={"request_id": "req_001"},
        )
    )

    assert response.status == "success"
    assert len(primary_provider.requests) == 1
    assert fallback_provider.last_request is not None
    assert fallback_provider.last_request.model == "gpt-5.4-mini"
    assert fallback_provider.last_request.metadata["attempt_id"] == "req_001:fallback:1"
    assert fallback_provider.last_request.metadata["is_fallback"] is True

    settings_module.clear_settings_cache()


def test_generate_text_returns_deadline_exceeded_before_attempt() -> None:
    provider = RecordingProvider()
    service = LLMService(provider)

    response = service.generate_text(
        GenerateTextInput(
            system_prompt="Follow the schema.",
            user_prompt="Question and evidence.",
            overall_deadline_ms=0,
            metadata={"request_id": "req_001"},
        )
    )

    assert response.status == "failed"
    assert response.error is not None
    assert response.error.error_type == "deadline_exceeded"
    assert provider.last_request is None


def test_build_llm_service_uses_environment_backed_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        (
            "LLM_BASE_URL=https://kuaipao.ai/v1\n"
            "LLM_API_KEY=test-key\n"
            "LLM_MODEL_ID=gpt-5.4\n"
            "LLM_MODEL_MINI_ID=gpt-5.4-mini\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings_module, "DOTENV_PATH", env_path)
    settings_module.clear_settings_cache()

    service = build_llm_service()

    assert service.__class__.__name__ == "LLMService"
    assert service._provider.__class__.__name__ == "OpenAICompatibleProvider"
    assert service._fallback_provider.__class__.__name__ == "OpenAICompatibleProvider"

    settings_module.clear_settings_cache()
