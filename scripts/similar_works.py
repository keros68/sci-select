"""Discover candidate journals from recent, similar OpenAlex works."""
from __future__ import annotations

import os
import re
import time
from datetime import date
from typing import Dict, Iterable, List

import requests


OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def build_search_queries(profile: Dict, max_queries: int = 3) -> List[str]:
    """Build compact literature queries, preferring an AI-structured profile."""
    supplied = _clean_queries(profile.get("search_queries", []))
    if supplied:
        return supplied[:max_queries]

    object_text = _clean_phrase(profile.get("research_object") or profile.get("primary_signal"))
    specialty = _clean_phrase(profile.get("specialty"))
    question = _clean_phrase(profile.get("research_question"))
    contribution = _clean_phrase(profile.get("contribution_type"))
    topics = [_clean_phrase(value) for value in profile.get("topic_evidence", []) if value]

    queries = []
    _append_query(queries, [object_text, specialty, question])
    _append_query(queries, [object_text, specialty, contribution])
    _append_query(queries, [object_text, *topics[:4]])
    return _clean_queries(queries)[:max_queries]


def discover_journal_candidates(
    search_queries: Iterable[str],
    years_back: int = 5,
    per_query: int = 50,
    max_journals: int = 20,
    timeout: int = 25,
    excluded_titles: Iterable[str] = (),
    excluded_work_ids: Iterable[str] = (),
) -> Dict:
    """Aggregate journals that recently published works matching multiple queries."""
    queries = _clean_queries(search_queries)
    if not queries:
        return {"queries": [], "candidates": [], "errors": ["未生成相似论文检索式"]}

    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    earliest_year = date.today().year - max(1, int(years_back)) - 1
    journals: Dict[str, Dict] = {}
    errors: List[str] = []
    excluded_title_keys = {_normalize_name(value) for value in excluded_titles or [] if value}
    excluded_id_keys = {_normalize_work_id(value) for value in excluded_work_ids or [] if value}

    for query_index, query in enumerate(queries):
        params = {
            "search": query,
            "filter": f"publication_year:>{earliest_year}",
            "sort": "relevance_score:desc",
            "per-page": max(5, min(int(per_query), 100)),
            "select": (
                "id,display_name,publication_year,type,is_retracted,relevance_score,"
                "primary_location,primary_topic"
            ),
        }
        if api_key:
            params["api_key"] = api_key
        if mailto:
            params["mailto"] = mailto

        try:
            payload = _get_openalex_payload(params, timeout)
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"OpenAlex相似论文检索失败[{query_index + 1}]: {exc}")
            continue

        for rank, work in enumerate(payload.get("results", []), 1):
            if work.get("is_retracted"):
                continue
            if work.get("type") not in ("article", "review", None, ""):
                continue
            if _normalize_work_id(work.get("id", "")) in excluded_id_keys:
                continue
            if _normalize_name(work.get("display_name", "")) in excluded_title_keys:
                continue

            location = work.get("primary_location") or {}
            source = location.get("source") or {}
            if source.get("type") != "journal" or not source.get("display_name"):
                continue

            source_key = source.get("id") or _normalize_name(source.get("display_name"))
            if not source_key:
                continue
            entry = journals.setdefault(source_key, _new_candidate(source))
            entry["_query_indexes"].add(query_index)
            entry["_best_rank"] = min(entry["_best_rank"], rank)
            entry["_rank_signal"] += 1.0 / rank

            work_id = work.get("id", "")
            if work_id and work_id in entry["_work_ids"]:
                continue
            if work_id:
                entry["_work_ids"].add(work_id)

            topic = (work.get("primary_topic") or {}).get("display_name", "")
            if topic:
                entry["_topics"].add(topic)
            entry["publication_precedents"].append(
                {
                    "title": work.get("display_name", ""),
                    "year": work.get("publication_year"),
                    "topic": topic,
                    "openalex_id": work_id,
                    "query": query,
                }
            )

    candidates = [_finish_candidate(entry) for entry in journals.values()]
    candidates = [
        entry
        for entry in candidates
        if entry["similar_works_count"] >= 2
        or entry["query_coverage"] >= 2
        or entry["_best_rank"] <= 3
    ]
    candidates.sort(
        key=lambda entry: (
            -entry["query_coverage"],
            -entry["similar_works_count"],
            -entry["literature_evidence_score"],
            entry["_best_rank"],
        )
    )
    for entry in candidates:
        for private_key in ("_query_indexes", "_work_ids", "_topics", "_rank_signal", "_best_rank"):
            entry.pop(private_key, None)

    return {
        "queries": queries,
        "candidates": candidates[: max(1, int(max_journals))],
        "errors": errors,
    }


def _new_candidate(source: Dict) -> Dict:
    issns = [str(value) for value in source.get("issn", []) if value]
    issn_l = str(source.get("issn_l") or "")
    return {
        "name": source.get("display_name", ""),
        "issn": issn_l or (issns[0] if issns else ""),
        "eissn": next((value for value in issns if value != issn_l), ""),
        "openalex_source_id": source.get("id", ""),
        "publication_precedents": [],
        "_query_indexes": set(),
        "_work_ids": set(),
        "_topics": set(),
        "_rank_signal": 0.0,
        "_best_rank": 10**6,
        "_sources": ["openalex-works"],
    }


def _finish_candidate(entry: Dict) -> Dict:
    count = len(entry["publication_precedents"])
    coverage = len(entry["_query_indexes"])
    evidence_score = min(
        28,
        min(count, 3) * 3 + coverage * 5 + min(6, round(entry["_rank_signal"] * 3)),
    )
    entry["similar_works_count"] = count
    entry["query_coverage"] = coverage
    entry["literature_evidence_score"] = evidence_score
    entry["openalex_topics"] = sorted(entry["_topics"])
    entry["field"] = "; ".join(entry["openalex_topics"][:4])
    entry["publication_precedents"] = sorted(
        entry["publication_precedents"],
        key=lambda work: (-(work.get("year") or 0), work.get("title", "")),
    )[:5]
    return entry


def _append_query(queries: List[str], parts: Iterable[str]) -> None:
    words = []
    for part in parts:
        if not part:
            continue
        for word in str(part).split():
            if word.lower() not in {value.lower() for value in words}:
                words.append(word)
    query = " ".join(words[:12]).strip()
    if query:
        queries.append(query)


def _clean_queries(values: Iterable[str]) -> List[str]:
    if isinstance(values, str):
        values = [values]
    cleaned = []
    for value in values or []:
        query = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(query) >= 3 and query.lower() not in {item.lower() for item in cleaned}:
            cleaned.append(query)
    return cleaned


def _clean_phrase(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _normalize_work_id(value: str) -> str:
    return str(value or "").strip().lower().rstrip("/")


def _get_openalex_payload(params: Dict, timeout: int, max_attempts: int = 3) -> Dict:
    retryable = {429, 500, 502, 503, 504}
    for attempt in range(max_attempts):
        response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=timeout)
        if response.status_code not in retryable or attempt == max_attempts - 1:
            response.raise_for_status()
            return response.json()

        retry_after = 0.0
        headers = getattr(response, "headers", {}) or {}
        try:
            retry_after = float(headers.get("Retry-After", 0) or 0)
        except (TypeError, ValueError):
            retry_after = 0.0
        time.sleep(min(10.0, max(retry_after, 1.0 * (2**attempt))))
    return {"results": []}
