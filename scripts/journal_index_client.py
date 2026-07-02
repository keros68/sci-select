"""Bundled, local, and static journal index reader.

Runtime prefers a user-configured sci-select SQLite index, then a user-configured
JSON index, then the bundled sci-select SQLite index shipped in assets/. JSON
remains supported via SCI_SELECT_JOURNAL_INDEX_PATH or SCI_SELECT_JOURNAL_INDEX_URL.
"""
import json
import os
import re
import sqlite3
from functools import lru_cache
from typing import Dict, List, Optional
from urllib import request


BUNDLED_SQLITE_INDEX = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "sci_select_journals.sqlite")
)


def lookup_index_journal(journal_name: str, issn: str = "") -> Optional[Dict]:
    configured_db = _configured_sqlite_source()
    if configured_db:
        row = _lookup_sqlite_journal(configured_db, journal_name, issn)
        if row:
            return _to_metrics(row)

    source = _index_source()
    rows = _load_index_rows(source) if source else []
    if rows:
        normalized_issn = _normalize_issn(issn)
        normalized_name = _normalize_name(journal_name)

        if normalized_issn:
            for row in rows:
                if normalized_issn in {
                    _normalize_issn(row.get("issn", "")),
                    _normalize_issn(row.get("eissn", "")),
                }:
                    return _to_metrics(row)

        for row in rows:
            if normalized_name and normalized_name == _normalize_name(row.get("title", "")):
                return _to_metrics(row)

    bundled_db = _bundled_sqlite_source()
    if bundled_db:
        row = _lookup_sqlite_journal(bundled_db, journal_name, issn)
        if row:
            return _to_metrics(row)

    return None


@lru_cache(maxsize=4)
def _load_index_rows(source: str) -> List[Dict]:
    try:
        if source.startswith(("http://", "https://")):
            with request.urlopen(source, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8-sig"))
        else:
            with open(source, "r", encoding="utf-8-sig") as f:
                payload = json.load(f)
    except (OSError, json.JSONDecodeError, TimeoutError):
        return []

    if isinstance(payload, dict):
        rows = payload.get("journals", [])
    else:
        rows = payload
    return [row for row in rows if isinstance(row, dict)]


def _index_source() -> str:
    return (
        os.environ.get("SCI_SELECT_JOURNAL_INDEX_PATH", "").strip()
        or os.environ.get("SCI_SELECT_JOURNAL_INDEX_URL", "").strip()
    )


def _configured_sqlite_source() -> str:
    return os.environ.get("SCI_SELECT_JOURNAL_INDEX_DB", "").strip()


def _bundled_sqlite_source() -> str:
    return BUNDLED_SQLITE_INDEX if os.path.exists(BUNDLED_SQLITE_INDEX) else ""


def _lookup_sqlite_journal(source: str, journal_name: str, issn: str = "") -> Optional[Dict]:
    if not os.path.exists(source):
        return None

    normalized_issn = _normalize_issn(issn)
    normalized_name = _normalize_name(journal_name)
    conn = None
    try:
        conn = sqlite3.connect(source)
        conn.row_factory = sqlite3.Row
        if normalized_issn:
            row = conn.execute(
                """
                SELECT payload_json FROM journals
                WHERE normalized_issn = ? OR normalized_eissn = ?
                LIMIT 1
                """,
                (normalized_issn, normalized_issn),
            ).fetchone()
            if row:
                return json.loads(row["payload_json"])

        if normalized_name:
            row = conn.execute(
                """
                SELECT payload_json FROM journals
                WHERE normalized_title = ?
                LIMIT 1
                """,
                (normalized_name,),
            ).fetchone()
            if row:
                return json.loads(row["payload_json"])
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        return None
    finally:
        if conn is not None:
            conn.close()
    return None


def _to_metrics(row: Dict) -> Dict:
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    metrics = {
        "name": row.get("title") or row.get("name") or "",
        "issn": row.get("issn", ""),
        "eissn": row.get("eissn", ""),
        "impact_factor": row.get("jif_2025") or row.get("if_2023") or row.get("impact_factor"),
        "if_year": str(row.get("jcr_data_year") or row.get("if_year") or ""),
        "jcr_release_year": row.get("jcr_release_year"),
        "jcr_data_year": row.get("jcr_data_year"),
        "jcr_quartile": row.get("jcr_quartile_2025") or row.get("jcr_quartile", ""),
        "jcr_categories": row.get("jcr_categories", []),
        "cas_partition_2025": row.get("cas_2025", ""),
        "partition": row.get("cas_2025", ""),
        "xinrui_partition_2026": row.get("xuankan_2026", ""),
        "nature_index": bool(row.get("nature_index")),
        "nature_index_year": row.get("nature_index_year"),
        "nature_index_articles": row.get("nature_index_articles"),
        "nature_index_publication_type": row.get("nature_index_publication_type"),
        "nature_index_source_url": row.get("nature_index_source_url"),
        "warning": bool(row.get("warning_latest") or row.get("xuankan_warning")),
        "journal_index_tags": tags,
    }
    sci_type = _sci_type_from_tags(tags)
    if sci_type:
        metrics["sci_type"] = sci_type
    return {k: v for k, v in metrics.items() if v not in ("", None, [])}


def _sci_type_from_tags(tags: List[str]) -> str:
    normalized = {str(tag).upper().replace(" ", "") for tag in tags}
    for label in ("SCIE", "SSCI", "ESCI", "AHCI", "SCI"):
        if label in normalized:
            return label
    return ""


def _normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
