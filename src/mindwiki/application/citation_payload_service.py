"""Citation payload builder for step 9.6."""

from __future__ import annotations

from mindwiki.application.retrieval_models import (
    CitationBuildResult,
    CitationPayload,
    ContextBuildResult,
)


class CitationPayloadService:
    """Build citation payloads from structured context sections."""

    def build_citations(self, context_result: ContextBuildResult) -> CitationBuildResult:
        citations: list[CitationPayload] = []
        counter = 1
        for section in context_result.sections:
            for item in section.evidence_items:
                primary_chunk_id = item.chunk_ids[0]
                citations.append(
                    CitationPayload(
                        citation_id=f"cit_{counter:03d}",
                        sub_query_id=section.sub_query_id,
                        chunk_id=primary_chunk_id,
                        document_id=item.document_id,
                        section_id=item.section_id,
                        document_title=item.document_title,
                        section_title=item.section_title,
                        source_type=item.source_type,
                        snippet=_build_snippet(item.chunk_text),
                        match_sources=("chunk_text",),
                        evidence_role=item.evidence_role,
                        location=item.location,
                    )
                )
                counter += 1
        return CitationBuildResult(citations=tuple(citations))


def _build_snippet(text: str, max_length: int = 180) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3].rstrip()}..."
