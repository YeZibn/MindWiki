"""Rule-first query decomposition for step 9.1 retrieval orchestration."""

from __future__ import annotations

import re

from mindwiki.application.retrieval_models import QueryDecomposition


_MAX_SUB_QUERIES = 3
_COMPARE_KEYWORDS = ("区别", "不同", "差异", "对比", "比较")
_MULTI_POINT_KEYWORDS = ("并且", "同时", "以及", "并说明", "分别说明")
_REVIEW_KEYWORDS = ("之前怎么讨论过", "有哪些结论", "历次提到", "整理一下相关内容")
_SUMMARY_PREFIXES = ("分别总结", "分别说明")
_PRONOUN_PREFIXES = ("它", "其", "两者", "这些", "那些", "该")


class QueryDecompositionService:
    """Apply first-stage decomposition heuristics before query expansion."""

    def decompose(self, query: str) -> QueryDecomposition:
        normalized_query = _normalize_query(query)
        if not normalized_query:
            return QueryDecomposition(query=query)

        comparison_sub_queries = _try_decompose_comparison(normalized_query)
        if comparison_sub_queries:
            return QueryDecomposition(
                query=query,
                decomposition_mode="decompose",
                sub_queries=comparison_sub_queries,
                reason="comparison_detected",
            )

        summary_sub_queries = _try_decompose_prefixed_summary(normalized_query)
        if summary_sub_queries:
            return QueryDecomposition(
                query=query,
                decomposition_mode="decompose",
                sub_queries=summary_sub_queries,
                reason="multi_object_summary_detected",
            )

        multi_point_sub_queries = _try_decompose_multi_point(normalized_query)
        if multi_point_sub_queries:
            return QueryDecomposition(
                query=query,
                decomposition_mode="decompose",
                sub_queries=multi_point_sub_queries,
                reason="multi_point_detected",
            )

        if any(keyword in normalized_query for keyword in _REVIEW_KEYWORDS):
            return QueryDecomposition(
                query=query,
                decomposition_mode="none",
                reason="review_query_kept_whole_in_first_stage",
            )

        return QueryDecomposition(query=query, decomposition_mode="none")


def build_query_decomposition_service() -> QueryDecompositionService:
    """Build the first-stage rule-based decomposition service."""

    return QueryDecompositionService()


def _try_decompose_comparison(query: str) -> tuple[str, ...]:
    if not any(keyword in query for keyword in _COMPARE_KEYWORDS):
        return ()

    objects_match = re.search(
        r"^(?P<left>.+?)和(?P<right>.+?)(?:有?什么)?(?:区别|不同|差异|对比|比较).*$",
        query,
    )
    if objects_match is None:
        return ()

    left = _strip_object_phrase(objects_match.group("left"))
    right = _strip_object_phrase(objects_match.group("right"))
    if not left or not right:
        return ()

    sub_queries = (
        f"{left}的职责边界或核心特点是什么？",
        f"{right}的职责边界或核心特点是什么？",
    )
    return _validate_sub_queries(sub_queries)


def _try_decompose_prefixed_summary(query: str) -> tuple[str, ...]:
    prefix = next((item for item in _SUMMARY_PREFIXES if query.startswith(item)), None)
    if prefix is None:
        return ()

    body = _normalize_query(query[len(prefix) :])
    if "的" not in body:
        return ()

    objects_part, suffix = body.rsplit("的", maxsplit=1)
    objects = _split_object_list(objects_part)
    if len(objects) < 2:
        return ()

    suffix_text = f"的{suffix}"
    sub_queries = tuple(f"{item}{suffix_text}" for item in objects[:_MAX_SUB_QUERIES])
    return _validate_sub_queries(sub_queries)


def _try_decompose_multi_point(query: str) -> tuple[str, ...]:
    if not any(keyword in query for keyword in _MULTI_POINT_KEYWORDS):
        return ()

    clauses = _split_multi_point_clauses(query)
    if len(clauses) < 2:
        return ()

    return _validate_sub_queries(tuple(clauses[:_MAX_SUB_QUERIES]))


def _split_multi_point_clauses(query: str) -> tuple[str, ...]:
    split_query = query
    for keyword in _MULTI_POINT_KEYWORDS:
        split_query = split_query.replace(keyword, "|")

    clauses = tuple(_normalize_clause(item) for item in split_query.split("|"))
    clauses = tuple(item for item in clauses if item)
    if len(clauses) < 2:
        return ()

    if any(clause.startswith(_PRONOUN_PREFIXES) for clause in clauses[1:]):
        return ()

    return clauses


def _split_object_list(objects_part: str) -> tuple[str, ...]:
    normalized = objects_part.replace("以及", "|").replace("和", "|").replace("、", "|")
    items = tuple(_strip_object_phrase(item) for item in normalized.split("|"))
    return tuple(item for item in items if item)


def _validate_sub_queries(sub_queries: tuple[str, ...]) -> tuple[str, ...]:
    if len(sub_queries) < 2 or len(sub_queries) > _MAX_SUB_QUERIES:
        return ()

    normalized_sub_queries = tuple(_normalize_clause(item) for item in sub_queries)
    if any(not item for item in normalized_sub_queries):
        return ()

    if len(set(normalized_sub_queries)) != len(normalized_sub_queries):
        return ()

    return normalized_sub_queries


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().split()).strip("。！？；;")


def _normalize_clause(clause: str) -> str:
    normalized = _normalize_query(clause).strip("，,")
    if not normalized:
        return ""
    if normalized.endswith(("？", "?")):
        return normalized.replace("?", "？")
    return f"{normalized}？"


def _strip_object_phrase(text: str) -> str:
    return text.strip().strip("，,。！？；; ")
