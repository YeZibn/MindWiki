"""Fixed query expansion for step 9.2 retrieval orchestration."""

from __future__ import annotations

from mindwiki.application.retrieval_models import QueryExpansion
from mindwiki.llm.service import GenerateTextInput, LLMService, build_llm_service


_QUERY_EXPANSION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "query_expansion",
        "schema": {
            "type": "object",
            "required": ["step_back_query", "hyde_query"],
            "properties": {
                "step_back_query": {"type": "string"},
                "hyde_query": {"type": "string"},
            },
        },
    },
}

_SYSTEM_PROMPT = """You generate retrieval query expansions for a personal knowledge base RAG system.

Return strict JSON only.
Generate exactly one `step_back_query` and one `hyde_query`.

Rules:
- `step_back_query` must be more abstract than the input query.
- Keep the same core object and topic constraints.
- Do not rewrite into a broad unrelated topic.
- `hyde_query` must be a short hypothetical answer paragraph in Chinese.
- `hyde_query` is for vector retrieval only and must stay grounded in the input topic.
- Do not add markdown fences.
"""


class QueryExpansionService:
    """Generate fixed `base / step-back / HyDE` queries for one retrieval unit."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def expand(self, query: str) -> QueryExpansion:
        normalized_query = _normalize_query(query)
        if not normalized_query:
            return QueryExpansion(
                query=query,
                base_query=query,
                step_back_query=query,
                hyde_query=query,
            )

        response = self._llm_service.generate_text(
            GenerateTextInput(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=(
                    "请基于下面的检索单元生成固定扩展。\n"
                    f"base_query: {normalized_query}\n"
                    "返回字段：step_back_query, hyde_query"
                ),
                task_type="query_expansion",
                response_format=_QUERY_EXPANSION_SCHEMA,
                temperature=0.1,
                max_tokens=512,
                allow_fallback=True,
                metadata={
                    "interface_name": "query_expansion",
                    "query": normalized_query,
                },
            )
        )

        if response.status != "success" or not isinstance(response.parsed_output, dict):
            error_details = ""
            if response.error is not None and response.error.message:
                error_details = f": {response.error.error_type}: {response.error.message}"
            raise RuntimeError(f"Failed to generate query expansion{error_details}")

        step_back_query = _normalize_query(str(response.parsed_output["step_back_query"]))
        hyde_query = _normalize_text(str(response.parsed_output["hyde_query"]))
        if not step_back_query or not hyde_query:
            raise RuntimeError("Generated query expansion is empty.")

        return QueryExpansion(
            query=query,
            base_query=normalized_query,
            step_back_query=step_back_query,
            hyde_query=hyde_query,
            use_step_back=True,
            use_hyde=True,
        )


def build_query_expansion_service() -> QueryExpansionService:
    """Build the first-stage fixed query expansion service."""

    llm_service = build_llm_service()
    return QueryExpansionService(llm_service)


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().split()).strip()


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split()).strip()
