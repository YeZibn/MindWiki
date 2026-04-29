from __future__ import annotations

from mindwiki.llm.embedding_models import EmbeddingRequest, EmbeddingResponse, EmbeddingVector
from mindwiki.llm.embedding_service import EmbeddingService, GenerateEmbeddingsInput


class RecordingEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[EmbeddingRequest] = []

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.calls.append(request)
        return EmbeddingResponse(
            model=request.model,
            provider="test_provider",
            vectors=tuple(
                EmbeddingVector(index=index, vector=(float(index + 1), float(index + 2)))
                for index, _ in enumerate(request.texts)
            ),
        )


def test_embedding_service_builds_request_from_payload() -> None:
    provider = RecordingEmbeddingProvider()
    service = EmbeddingService(provider)

    response = service.generate_embeddings(
        GenerateEmbeddingsInput(
            texts=("a", "b"),
            model="embed-model",
            timeout_ms=4567,
            metadata={"request_id": "emb_001"},
        )
    )

    assert response.provider == "test_provider"
    assert len(response.vectors) == 2
    request = provider.calls[0]
    assert request.model == "embed-model"
    assert request.timeout_ms == 4567
    assert request.metadata["request_id"] == "emb_001"

