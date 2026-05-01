"""First-stage answer generation service for step 10 QA only."""

from __future__ import annotations

import json

from mindwiki.application.retrieval_models import (
    ANSWER_CONFIDENCE_VALUES,
    AnswerGenerationResult,
    CitationBuildResult,
    CitationPayload,
    ContextBuildResult,
)
from mindwiki.llm.service import GenerateTextInput, LLMService, build_llm_service

_ANSWER_GENERATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "rag_answer",
        "schema": {
            "type": "object",
            "required": ["answer", "sources", "confidence"],
            "properties": {
                "answer": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["citation_id"],
                        "properties": {
                            "citation_id": {"type": "string"},
                        },
                    },
                },
                "confidence": {"type": "string"},
            },
        },
    },
}

_SYSTEM_PROMPT = """You answer questions for a personal knowledge base RAG system.

Return strict JSON only.
You must answer only from the provided evidence.
You must not invent facts, sources, or conclusions beyond the provided context.
If the evidence is insufficient or conflicting, you must refuse to answer with the approved no-answer message.

Rules:
- Output fields: answer, sources, confidence.
- `sources` must contain only citation ids from the provided citation list.
- Do not output citation ids that are not provided.
- Prefer the minimum source set needed to support the answer.
- If the evidence is insufficient, answer exactly: `当前检索到的知识不足以可靠回答这个问题。`
- If the evidence is conflicting, answer exactly: `当前检索到的知识存在冲突，暂时无法给出可靠结论。`
- If you output a no-answer message, `sources` must be an empty list and `confidence` must be `low`.
- `confidence` must be exactly one of: high, medium, low.
- Do not add markdown fences.
"""

_EMPTY_RETRIEVAL_TEXT = "当前知识库中没有检索到可用于回答该问题的相关内容。"
_INSUFFICIENT_EVIDENCE_TEXT = "当前检索到的知识不足以可靠回答这个问题。"
_CONFLICTING_EVIDENCE_TEXT = "当前检索到的知识存在冲突，暂时无法给出可靠结论。"
_GENERATION_DEGRADED_TEXT = "当前暂时无法基于现有知识给出可靠回答。"
_NO_ANSWER_TEXTS = frozenset(
    {
        _EMPTY_RETRIEVAL_TEXT,
        _INSUFFICIENT_EVIDENCE_TEXT,
        _CONFLICTING_EVIDENCE_TEXT,
        _GENERATION_DEGRADED_TEXT,
    }
)


class AnswerGenerationService:
    """Generate a structured QA answer from built context and citations."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def generate_answer(
        self,
        *,
        question: str,
        context_result: ContextBuildResult,
        citation_result: CitationBuildResult,
    ) -> AnswerGenerationResult:
        normalized_question = _normalize_text(question)
        if not normalized_question:
            raise ValueError("Question must not be empty.")

        if not context_result.sections:
            return _build_no_answer_result(
                question=normalized_question,
                answer=_EMPTY_RETRIEVAL_TEXT,
            )
        if not citation_result.citations:
            return _build_no_answer_result(
                question=normalized_question,
                answer=_INSUFFICIENT_EVIDENCE_TEXT,
            )

        response = self._llm_service.generate_text(
            GenerateTextInput(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=self._build_user_prompt(
                    question=normalized_question,
                    context_result=context_result,
                    citation_result=citation_result,
                ),
                task_type="rag_answer",
                response_format=_ANSWER_GENERATION_SCHEMA,
                temperature=0.1,
                max_tokens=1024,
                allow_fallback=True,
                metadata={
                    "interface_name": "answer_generation",
                    "question": normalized_question,
                },
            )
        )

        if response.status != "success" or not isinstance(response.parsed_output, dict):
            return _build_no_answer_result(
                question=normalized_question,
                answer=_GENERATION_DEGRADED_TEXT,
            )

        answer_text = _normalize_text(str(response.parsed_output["answer"]))
        if not answer_text:
            return _build_no_answer_result(
                question=normalized_question,
                answer=_GENERATION_DEGRADED_TEXT,
            )

        confidence = _normalize_text(str(response.parsed_output["confidence"])).lower()
        if confidence not in ANSWER_CONFIDENCE_VALUES:
            return _build_no_answer_result(
                question=normalized_question,
                answer=_GENERATION_DEGRADED_TEXT,
            )

        try:
            selected_sources = self._map_sources(
                response.parsed_output["sources"],
                citation_result,
            )
        except RuntimeError:
            return _build_no_answer_result(
                question=normalized_question,
                answer=_GENERATION_DEGRADED_TEXT,
            )

        if not selected_sources:
            if answer_text in _NO_ANSWER_TEXTS:
                return _build_no_answer_result(
                    question=normalized_question,
                    answer=answer_text,
                )
            return _build_no_answer_result(
                question=normalized_question,
                answer=_INSUFFICIENT_EVIDENCE_TEXT,
            )

        return AnswerGenerationResult(
            question=normalized_question,
            answer=answer_text,
            sources=selected_sources,
            confidence=confidence,
        )

    @staticmethod
    def _build_user_prompt(
        *,
        question: str,
        context_result: ContextBuildResult,
        citation_result: CitationBuildResult,
    ) -> str:
        context_payload = [
            {
                "sub_query_id": section.sub_query_id,
                "sub_query_text": section.sub_query_text,
                "evidence_items": [
                    {
                        "document_title": item.document_title,
                        "section_title": item.section_title,
                        "chunk_text": item.chunk_text,
                        "evidence_role": item.evidence_role,
                        "rerank_score": item.rerank_score,
                    }
                    for item in section.evidence_items
                ],
            }
            for section in context_result.sections
        ]
        citation_payload = [
            {
                "citation_id": citation.citation_id,
                "document_title": citation.document_title,
                "section_title": citation.section_title,
                "snippet": citation.snippet,
                "evidence_role": citation.evidence_role,
            }
            for citation in citation_result.citations
        ]

        return (
            "请基于提供的知识片段回答问题。\n"
            f"question: {question}\n"
            "context_sections:\n"
            f"{json.dumps(context_payload, ensure_ascii=False, indent=2)}\n"
            "citations:\n"
            f"{json.dumps(citation_payload, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            "- 只能依据上述 context_sections 和 citations 回答。\n"
            "- 如果证据不足，必须返回：当前检索到的知识不足以可靠回答这个问题。\n"
            "- 如果证据存在冲突，必须返回：当前检索到的知识存在冲突，暂时无法给出可靠结论。\n"
            "- 返回无答案时，`sources` 必须为空数组，`confidence` 必须为 low。\n"
            "- `sources` 只返回真正支撑答案的 citation_id。\n"
            "- `confidence` 只能返回 high、medium、low。\n"
        )

    @staticmethod
    def _map_sources(
        raw_sources: object,
        citation_result: CitationBuildResult,
    ) -> tuple[CitationPayload, ...]:
        if not isinstance(raw_sources, list):
            raise RuntimeError("Generated sources must be a list.")

        citation_map = {
            citation.citation_id: citation
            for citation in citation_result.citations
        }
        selected: list[CitationPayload] = []
        seen_ids: set[str] = set()

        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                raise RuntimeError("Generated source item must be an object.")

            citation_id = _normalize_text(str(raw_source.get("citation_id", "")))
            if not citation_id:
                raise RuntimeError("Generated source item is missing citation_id.")
            if citation_id in seen_ids:
                continue

            citation = citation_map.get(citation_id)
            if citation is None:
                raise RuntimeError("Generated source references unknown citation_id.")

            selected.append(citation)
            seen_ids.add(citation_id)

        return tuple(selected)


def build_answer_generation_service() -> AnswerGenerationService:
    """Build the first-stage QA answer generation service."""

    llm_service = build_llm_service()
    return AnswerGenerationService(llm_service)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).strip()


def _build_no_answer_result(
    *,
    question: str,
    answer: str,
) -> AnswerGenerationResult:
    return AnswerGenerationResult(
        question=question,
        answer=answer,
        sources=(),
        confidence="low",
    )
