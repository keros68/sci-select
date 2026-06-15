"""Small LetPub public-data client used by sci-select."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE = "https://letpub.com.cn"
WWW_BASE = "https://www.letpub.com.cn"

HEADERS = {
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
    ),
}


def autocomplete_journal(name: str, timeout: int = 15) -> List[Dict]:
    response = requests.get(
        f"{BASE}/journalappAjax.php",
        params={"querytype": "autojournal", "term": name},
        headers={**HEADERS, "x-requested-with": "XMLHttpRequest"},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def advanced_search(
    searchname: str = "",
    searchissn: str = "",
    searchfield: str = "",
    searchimpactlow: str = "",
    searchimpacthigh: str = "",
    searchscitype: str = "",
    searchcategory1: str = "",
    searchcategory2: str = "",
    searchjcrkind: str = "",
    searchopenaccess: str = "",
    searchsort: str = "relevance",
    timeout: int = 20,
) -> Dict:
    response = requests.post(
        f"{WWW_BASE}/index.php?page=journalapp&view=search",
        data={
            "searchname": searchname,
            "searchissn": searchissn,
            "searchfield": searchfield,
            "searchimpactlow": searchimpactlow,
            "searchimpacthigh": searchimpacthigh,
            "searchscitype": searchscitype,
            "view": "search",
            "searchcategory1": searchcategory1,
            "searchcategory2": searchcategory2,
            "searchjcrkind": searchjcrkind,
            "searchopenaccess": searchopenaccess,
            "searchsort": searchsort,
        },
        headers={**HEADERS, "content-type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_search_results(response.text)


def parse_search_results(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    info_text = _clean(soup.get_text(" ", strip=True))
    total_records = _first_int(re.search(r"(\d+)条记录", info_text))
    total_pages = _first_int(re.search(r"共(\d+)页", info_text)) or 1

    table = soup.select_one("table.table_yjfx")
    journals: List[Dict] = []
    if not table:
        return {"journals": journals, "total_pages": total_pages, "total_records": total_records}

    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        name_link = cells[1].find("a")
        name = _clean(name_link.get_text(" ", strip=True)) if name_link else ""
        href = name_link.get("href", "") if name_link else ""
        stat_text = _clean(cells[3].get_text(" ", strip=True))

        journals.append(
            {
                "issn": _clean(cells[0].get_text(" ", strip=True)),
                "name": name,
                "journal_id": _extract_query_value(href, "journalid"),
                "shortname": _extract_shortname(cells[1]),
                "impact_factor": _first_number(_clean(cells[2].get_text(" ", strip=True))),
                "real_time_if": _match_text(r"IF:\s*([\d.]+)", stat_text),
                "h_index": _match_text(r"h-index:\s*(\d+)", stat_text),
                "cite_score": _match_text(r"CiteScore:\s*([\d.]+)", stat_text),
                "partition": _clean(cells[4].get_text(" ", strip=True)),
                "field": _clean(cells[5].get_text(" ", strip=True)),
                "sci_type": _clean(cells[6].get_text(" ", strip=True)),
            }
        )

    return {"journals": journals, "total_pages": total_pages, "total_records": total_records}


def lookup_journal(name: str) -> Optional[Dict]:
    candidates = autocomplete_journal(name)
    if not candidates:
        for sep in (" - ", ": ", " (", " – ", " / "):
            if sep in name:
                candidates = autocomplete_journal(name.split(sep)[0].strip())
                if candidates:
                    break

    search_hit = _best_search_hit(name)
    journal_id = ""
    if candidates:
        journal_id = str(candidates[0].get("id", ""))
    if not journal_id and search_hit:
        journal_id = search_hit.get("journal_id", "")
    if not journal_id:
        return None

    detail = get_journal_detail(journal_id)
    if not detail:
        detail = {}

    detail["_journal_id"] = journal_id
    if search_hit:
        for key in ("sci_type", "partition", "field", "impact_factor", "issn", "name", "shortname"):
            if search_hit.get(key) and not detail.get(key):
                detail[key] = search_hit[key]
        detail["_sci_type"] = search_hit.get("sci_type", "")

    if candidates and not detail.get("name"):
        detail["name"] = candidates[0].get("label") or candidates[0].get("value") or name
    return detail


def get_journal_detail(journal_id: str, timeout: int = 20) -> Dict:
    response = requests.get(
        f"{BASE}/index.php",
        params={"journalid": journal_id, "page": "journalapp", "view": "detail"},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_detail_page(response.text)


def parse_detail_page(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    detail: Dict = {}

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        label = _clean(cells[0].get_text(" ", strip=True))
        value_text = _clean(cells[1].get_text(" ", strip=True))

        if "期刊名字" in label:
            link = cells[1].find("a")
            detail["name"] = _clean(link.get_text(" ", strip=True)) if link else value_text
            detail["shortname"] = _extract_shortname(cells[1])
        elif "期刊ISSN" in label:
            detail["issn"] = value_text
        elif "最新影响因子" in label and "实时" not in label:
            detail["impact_factor"] = _first_number(value_text)
        elif "实时影响因子" in label:
            detail["real_time_if"] = _first_number(value_text)
        elif "五年影响因子" in label:
            detail["five_year_if"] = _first_number(value_text)
        elif "是否OA开放访问" in label:
            detail["open_access"] = "yes" in value_text.lower()
        elif "OA期刊相关信息" in label:
            detail["oa_price"] = _first_int(re.search(r"USD\s*([\d,]+)", value_text.replace(",", "")))
        elif "出版商" in label:
            detail["publisher"] = value_text
        elif "涉及的研究方向" in label:
            detail["field"] = value_text
        elif "期刊分区表预警名单" in label or "国际期刊预警名单" in label:
            detail["warning"] = bool(value_text and "不在预警名单中" not in value_text)
        elif "期刊分区表" in label and "2025" in label:
            detail["ch_sci_2025"] = _parse_partition(cells[1])
        elif "平均审稿速度" in label:
            detail["speed"] = value_text
        elif "平均录用比例" in label:
            detail["accept"] = value_text

    return detail


def _best_search_hit(name: str) -> Optional[Dict]:
    try:
        result = advanced_search(searchname=name, searchsort="relevance")
    except Exception:
        return None

    journals = result.get("journals", [])
    if not journals:
        return None

    normalized = _clean(name).lower()
    for journal in journals:
        candidate = journal.get("name", "").lower()
        if normalized == candidate or normalized in candidate or candidate in normalized:
            return journal
    return journals[0]


def _parse_partition(cell) -> Dict:
    text = _clean(cell.get_text(" ", strip=True))
    return {
        "大类学科": _match_text(r"([^\s\d]+)\s*\d区", text),
        "小类学科": _match_text(r"小类学科[:：]?\s*([^\s]+)", text),
        "分区": _match_text(r"([1-4]区)", text),
        "Top期刊": "Top" in text and "否" not in text,
        "综述期刊": "综述" in text and "否" not in text,
    }


def _extract_shortname(cell) -> str:
    grey = cell.select_one('font[color="grey"]')
    return _clean(grey.get_text(" ", strip=True)) if grey else ""


def _extract_query_value(href: str, key: str) -> str:
    match = re.search(rf"[?&]{re.escape(key)}=([^&]+)", href or "")
    return match.group(1) if match else ""


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _match_text(pattern: str, value: str) -> str:
    match = re.search(pattern, value or "", flags=re.I)
    return match.group(1).strip() if match else ""


def _first_number(value: str) -> str:
    return _match_text(r"([\d]+(?:\.\d+)?)", value)


def _first_int(match) -> int:
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
