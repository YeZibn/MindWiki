from __future__ import annotations

from pathlib import Path

from mindwiki.infrastructure import settings as settings_module
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
from mindwiki.llm.rerank_models import RerankDocument, RerankRequest, RerankResponse, RerankResult
from mindwiki.llm.providers.openai_compatible import OpenAICompatibleConfig


def test_llm_request_keeps_openai_compatible_fields() -> None:
    request = LLMRequest(
        task_type="qa",
        model="gpt-5.4",
        messages=(
            LLMMessage(role="system", content="Follow the schema."),
            LLMMessage(role="user", content="Question and context."),
        ),
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "rag_answer", "schema": {}},
        },
        retry_policy=RetryPolicy(max_retries=2, allow_fallback=True),
        metadata={"request_id": "req_001", "trace_id": "trace_001"},
    )

    assert request.task_type == "qa"
    assert request.model == "gpt-5.4"
    assert [message.role for message in request.messages] == ["system", "user"]
    assert request.response_format is not None
    assert request.response_format["type"] == "json_schema"
    assert request.retry_policy.max_retries == 2
    assert request.retry_policy.allow_fallback is True
    assert request.metadata["request_id"] == "req_001"


def test_llm_response_keeps_validation_and_error_fields() -> None:
    response = LLMResponse(
        request_id="req_001",
        model="gpt-5.4",
        output_text='{"answer":"done"}',
        status="failed",
        parsed_output=None,
        validation=LLMValidation(
            protocol_validation=ValidationResult(passed=True),
            schema_validation=ValidationResult(
                passed=False,
                issues=(
                    ValidationIssue(
                        code="json_decode_failed",
                        path="$.answer",
                        message="Output is not valid JSON.",
                    ),
                ),
            ),
            citation_validation=ValidationResult(passed=True),
            final_status="repairable",
        ),
        timing=ResponseTiming(latency_ms=812),
        error=LLMError(
            error_type="schema_validation_failed",
            retryable=False,
            fallback_allowed=True,
            message="Structured output is invalid.",
        ),
        provider_response_id="resp_001",
        finish_reason="stop",
        usage={"input_tokens": 120, "output_tokens": 42, "total_tokens": 162},
    )

    assert response.status == "failed"
    assert response.validation.final_status == "repairable"
    assert response.validation.schema_validation.passed is False
    assert response.validation.schema_validation.issues[0].code == "json_decode_failed"
    assert response.error is not None
    assert response.error.fallback_allowed is True
    assert response.timing.latency_ms == 812
    assert response.usage["total_tokens"] == 162


def test_settings_reads_llm_configuration_from_dotenv(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        (
            "MINDWIKI_DATABASE_URL=postgresql://postgres:password@localhost:5432/mindwiki\n"
            "LOG_LEVEL=DEBUG\n"
            "LOG_FORMAT=json\n"
            "LLM_BASE_URL=https://kuaipao.ai/v1\n"
            "LLM_API_KEY=test-key\n"
            "LLM_MODEL_ID=gpt-5.4\n"
            "LLM_MODEL_MINI_ID=gpt-5.4-mini\n"
            "LLM_TIMEOUT_MS=45000\n"
            "LLM_RERANK_BASE_URL=https://api.siliconflow.cn/v1\n"
            "LLM_RERANK_API_KEY=rerank-key\n"
            "LLM_RERANK_MODEL_ID=Qwen/Qwen3-Reranker-8B\n"
            "LLM_RERANK_TIMEOUT_MS=15000\n"
        ),
        encoding="utf-8",
    )

    for key in (
        "MINDWIKI_DATABASE_URL",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL_ID",
        "LLM_MODEL_MINI_ID",
        "LLM_TIMEOUT_MS",
        "LLM_RERANK_BASE_URL",
        "LLM_RERANK_API_KEY",
        "LLM_RERANK_MODEL_ID",
        "LLM_RERANK_TIMEOUT_MS",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(settings_module, "DOTENV_PATH", env_path)
    settings_module.clear_settings_cache()

    settings = settings_module.get_settings()

    assert settings.database_url == "postgresql://postgres:password@localhost:5432/mindwiki"
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"
    assert settings.llm_base_url == "https://kuaipao.ai/v1"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model_id == "gpt-5.4"
    assert settings.llm_model_mini_id == "gpt-5.4-mini"
    assert settings.llm_timeout_ms == 45000
    assert settings.llm_rerank_base_url == "https://api.siliconflow.cn/v1"
    assert settings.llm_rerank_api_key == "rerank-key"
    assert settings.llm_rerank_model_id == "Qwen/Qwen3-Reranker-8B"
    assert settings.llm_rerank_timeout_ms == 15000

    settings_module.clear_settings_cache()


def test_openai_compatible_config_accepts_settings_values() -> None:
    config = OpenAICompatibleConfig(
        base_url="https://kuaipao.ai/v1",
        api_key="test-key",
        default_model="gpt-5.4",
    )

    assert config.base_url == "https://kuaipao.ai/v1"
    assert config.api_key == "test-key"
    assert config.default_model == "gpt-5.4"


def test_rerank_request_and_response_keep_core_fields() -> None:
    request = RerankRequest(
        query="Step 8的职责？",
        documents=(
            RerankDocument(document_id="chunk_1", text="doc 1"),
            RerankDocument(document_id="chunk_2", text="doc 2"),
        ),
        model="Qwen/Qwen3-Reranker-8B",
        top_n=2,
        timeout_ms=12000,
        metadata={"request_id": "rerank_001"},
    )
    response = RerankResponse(
        model="Qwen/Qwen3-Reranker-8B",
        results=(
            RerankResult(index=1, document_id="chunk_2", relevance_score=0.92),
            RerankResult(index=0, document_id="chunk_1", relevance_score=0.71),
        ),
        usage={"total_tokens": 42},
    )

    assert request.query == "Step 8的职责？"
    assert request.documents[0].document_id == "chunk_1"
    assert request.top_n == 2
    assert response.results[0].document_id == "chunk_2"
    assert response.results[0].relevance_score == 0.92
