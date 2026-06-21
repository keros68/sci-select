"""Optional local/static journal index reader.

The index is a user-provided JSON file, not bundled data. Supported shapes:
{"meta": {...}, "journals": [...]} or a plain list of journal rows.
"""
import json
import os
import re
from functools import lru_cache
from typing import Dict, List, Optional
from urllib import request


def lookup_index_journal(journal_name: str, issn: str = "") -> Optional[Dict]:
    source = _index_source()
    rows = _load_index_rows(source) if source else []
    if not rows:
        return None

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


def _to_metrics(row: Dict) -> Dict:
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    metrics = {
        "name": row.get("title") or row.get("name") or "",
        "issn": row.get("issn", ""),
        "eissn": row.get("eissn", ""),
        "impact_factor": row.get("if_2023"),
        "if_year": row.get("if_year", ""),
        "jcr_quartile": row.get("jcr_quartile", ""),
        "cas_partition_2025": row.get("cas_2025", ""),
        "partition": row.get("cas_2025", ""),
        "xinrui_partition_2026": row.get("xuankan_2026", ""),
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
