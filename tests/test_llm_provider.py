from __future__ import annotations

import io
import json
from urllib import error

from mindwiki.llm.models import LLMMessage, LLMRequest, RetryPolicy
from mindwiki.llm.embedding_models import EmbeddingRequest
from mindwiki.llm.rerank_models import RerankDocument, RerankRequest
from mindwiki.llm.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleProvider,
    OpenAICompatibleRerankProvider,
)


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def build_request() -> LLMRequest:
    return LLMRequest(
        task_type="qa",
        model="gpt-5.4",
        messages=(
            LLMMessage(role="system", content="Follow the schema."),
            LLMMessage(role="user", content="Question and context."),
        ),
        response_format={"type": "json_schema", "json_schema": {"name": "answer", "schema": {}}},
        timeout_ms=12000,
        retry_policy=RetryPolicy(max_retries=2, allow_fallback=True),
        metadata={"request_id": "req_001"},
    )


def test_openai_compatible_provider_builds_chat_completions_payload() -> None:
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url="https://kuaipao.ai/v1",
            api_key="test-key",
        )
    )

    payload = provider.build_payload(build_request())

    assert payload["model"] == "gpt-5.4"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "Question and context."
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["max_tokens"] == 1024


def test_openai_compatible_provider_parses_success_response() -> None:
    def fake_urlopen(req, timeout):
        assert req.full_url == "https://kuaipao.ai/v1/chat/completions"
        assert timeout == 12.0
        assert req.get_header("Authorization") == "Bearer test-key"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "gpt-5.4"
        return FakeHTTPResponse(
            {
                "id": "chatcmpl_001",
                "model": "gpt-5.4",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": '{"answer":"done"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            }
        )

    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url="https://kuaipao.ai/v1",
            api_key="test-key",
        ),
        urlopen=fake_urlopen,
    )

    response = provider.generate(build_request())

    assert response.status == "success"
    assert response.output_text == '{"answer":"done"}'
    assert response.provider_response_id == "chatcmpl_001"
    assert response.finish_reason == "stop"
    assert response.validation.protocol_validation.passed is True
    assert response.usage["total_tokens"] == 120


def test_openai_compatible_provider_marks_missing_choice_as_protocol_failure() -> None:
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url="https://kuaipao.ai/v1",
            api_key="test-key",
        ),
        urlopen=lambda req, timeout: FakeHTTPResponse({"id": "chatcmpl_002", "choices": []}),
    )

    response = provider.generate(build_request())

    assert response.status == "failed"
    assert response.error is not None
    assert response.error.error_type == "protocol_validation_failed"
    assert response.validation.protocol_validation.passed is False
    assert response.validation.protocol_validation.issues[0].code == "missing_choice"


def test_openai_compatible_provider_maps_http_429_to_retryable_error() -> None:
    def fake_urlopen(req, timeout):
        raise error.HTTPError(
            req.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url="https://kuaipao.ai/v1",
            api_key="test-key",
        ),
        urlopen=fake_urlopen,
    )

    response = provider.generate(build_request())

    assert response.status == "failed"
    assert response.error is not None
    assert response.error.error_type == "http_error"
    assert response.error.retryable is True
    assert response.error.fallback_allowed is True


def test_openai_compatible_provider_maps_network_error() -> None:
    def fake_urlopen(req, timeout):
        raise error.URLError("connection reset")

    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            base_url="https://kuaipao.ai/v1",
            api_key="test-key",
        ),
        urlopen=fake_urlopen,
    )

    response = provider.generate(build_request())

    assert response.status == "failed"
    assert response.error is not None
    assert response.error.error_type == "network_error"
    assert response.error.retryable is True


def test_openai_compatible_embedding_provider_builds_payload_and_parses_response() -> None:
    def fake_urlopen(req, timeout):
        assert req.full_url == "https://api.siliconflow.cn/v1/embeddings"
        assert timeout == 8.0
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "Qwen/Qwen3-Embedding-8B"
        assert payload["input"] == ["A", "B"]
        return FakeHTTPResponse(
            {
                "model": "Qwen/Qwen3-Embedding-8B",
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2]},
                    {"index": 1, "embedding": [0.3, 0.4]},
                ],
                "usage": {"prompt_tokens": 12, "total_tokens": 12},
            }
        )

    provider = OpenAICompatibleEmbeddingProvider(
        OpenAICompatibleConfig(
            base_url="https://api.siliconflow.cn/v1",
            api_key="embed-key",
        ),
        urlopen=fake_urlopen,
    )

    response = provider.embed(
        EmbeddingRequest(
            model="Qwen/Qwen3-Embedding-8B",
            texts=("A", "B"),
            timeout_ms=8000,
        )
    )

    assert response.provider == "openai_compatible"
    assert response.model == "Qwen/Qwen3-Embedding-8B"
    assert response.usage["total_tokens"] == 12
    assert response.vectors[0].vector == (0.1, 0.2)


def test_openai_compatible_rerank_provider_builds_payload_and_parses_response() -> None:
    def fake_urlopen(req, timeout):
        assert req.full_url == "https://api.siliconflow.cn/v1/rerank"
        assert timeout == 15.0
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "Qwen/Qwen3-Reranker-8B"
        assert payload["query"] == "Step 8的职责？"
        assert payload["documents"] == ["doc 1", "doc 2"]
        assert payload["top_n"] == 2
        return FakeHTTPResponse(
            {
                "model": "Qwen/Qwen3-Reranker-8B",
                "results": [
                    {"index": 1, "relevance_score": 0.91},
                    {"index": 0, "relevance_score": 0.72},
                ],
                "usage": {"total_tokens": 21},
            }
        )

    provider = OpenAICompatibleRerankProvider(
        OpenAICompatibleConfig(
            base_url="https://api.siliconflow.cn/v1",
            api_key="rerank-key",
        ),
        urlopen=fake_urlopen,
    )

    response = provider.rerank(
        RerankRequest(
            query="Step 8的职责？",
            documents=(
                RerankDocument(document_id="chunk_1", text="doc 1"),
                RerankDocument(document_id="chunk_2", text="doc 2"),
            ),
            model="Qwen/Qwen3-Reranker-8B",
            top_n=2,
            timeout_ms=15000,
        )
    )

    assert response.model == "Qwen/Qwen3-Reranker-8B"
    assert response.results[0].document_id == "chunk_2"
    assert response.results[0].relevance_score == 0.91
    assert response.results[1].document_id == "chunk_1"
    assert response.usage["total_tokens"] == 21
