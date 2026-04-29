from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mindwiki.application.retrieval_models import RetrievalFilters, TimeRange
from mindwiki.infrastructure.retrieval_repository import build_bm25_query, build_projection_query


def test_build_projection_query_without_optional_filters() -> None:
    query = build_projection_query(RetrievalFilters(), limit=25)

    assert "FROM chunks c" in query.sql
    assert "JOIN documents d ON d.id = c.document_id" in query.sql
    assert "ARRAY_AGG(DISTINCT t.tag_name)" in query.sql
    assert "src.source_type = ANY(%s)" not in query.sql
    assert "d.id = ANY(%s)" not in query.sql
    assert "dt_filter.document_id = d.id" not in query.sql
    assert query.params == (25,)


def test_build_projection_query_includes_strong_filters() -> None:
    start_time = datetime(2026, 4, 1, 0, 0, 0)
    end_time = datetime(2026, 4, 30, 23, 59, 59)
    filters = RetrievalFilters(
        tags=("work", "rag"),
        source_types=("markdown", "pdf"),
        document_scope=(UUID("00000000-0000-0000-0000-000000000011"),),
        time_range=TimeRange(start_time=start_time, end_time=end_time),
    )

    query = build_projection_query(filters, limit=10)

    assert "src.source_type = ANY(%s)" in query.sql
    assert "d.id = ANY(%s)" in query.sql
    assert "dt_filter.document_id = d.id" in query.sql
    assert "d.imported_at >= %s" in query.sql
    assert "d.imported_at <= %s" in query.sql
    assert query.params == (
        ["markdown", "pdf"],
        [UUID("00000000-0000-0000-0000-000000000011")],
        ["work", "rag"],
        start_time,
        end_time,
        10,
    )


def test_build_bm25_query_uses_weighted_postgres_full_text_search() -> None:
    query = build_bm25_query("rag retrieval", RetrievalFilters(), limit=5)

    assert "ts_rank_cd(" in query.sql
    assert "setweight(to_tsvector('simple', COALESCE(document_title, '')), 'A')" in query.sql
    assert "setweight(to_tsvector('simple', COALESCE(section_title, '')), 'B')" in query.sql
    assert "setweight(to_tsvector('simple', COALESCE(document_tags_text, '')), 'C')" in query.sql
    assert "setweight(to_tsvector('simple', COALESCE(chunk_text, '')), 'D')" in query.sql
    assert "websearch_to_tsquery('simple', %s)" in query.sql
    assert "WHERE bm25_score > 0" in query.sql
    assert "ORDER BY" in query.sql
    assert query.params == ("rag retrieval", "rag retrieval", "rag retrieval", "rag retrieval", "rag retrieval", 5)


def test_build_bm25_query_keeps_strong_filters_before_ranking() -> None:
    start_time = datetime(2026, 4, 1, 0, 0, 0)
    filters = RetrievalFilters(
        tags=("work",),
        source_types=("markdown",),
        document_scope=(UUID("00000000-0000-0000-0000-000000000011"),),
        time_range=TimeRange(start_time=start_time),
    )

    query = build_bm25_query("contract", filters, limit=3)

    assert "src.source_type = ANY(%s)" in query.sql
    assert "d.id = ANY(%s)" in query.sql
    assert "dt_filter.document_id = d.id" in query.sql
    assert "d.imported_at >= %s" in query.sql
    assert query.params == (
        ["markdown"],
        [UUID("00000000-0000-0000-0000-000000000011")],
        ["work"],
        start_time,
        "contract",
        "contract",
        "contract",
        "contract",
        "contract",
        3,
    )
