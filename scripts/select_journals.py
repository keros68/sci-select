"""
sci-aiselect main selector.

The public API is intentionally small:
- infer_paper_profile(text): understand paper topics and candidate LetPub categories
- select_journals(text, ...): live LetPub/OpenAlex workflow
- rank_metric_records(profile, records): deterministic scoring for tested/reportable results
- format_selection_report(profile, ranked): user-facing report
"""
from __future__ import annotations

import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

from .journal_metrics import get_journal_metrics, format_metrics_line
from .letpub_client import advanced_search


Category = Dict[str, str]
MetricRecord = Dict


TERM_RULES: List[Dict] = [
    {
        "label": "groundwater",
        "aliases": ["地下水", "groundwater", "aquifer", "phreatic water"],
        "categories": [("环境科学与生态学", "水资源")],
        "weight": 4,
    },
    {
        "label": "hydrology",
        "aliases": ["水文", "hydrology", "hydrological", "watershed", "catchment", "basin"],
        "categories": [("环境科学与生态学", "水资源")],
        "weight": 3,
    },
    {
        "label": "hydrochemistry",
        "aliases": ["水化学", "hydrochemistry", "hydrochemical", "water chemistry"],
        "categories": [("地球科学", "地球化学与地球物理"), ("环境科学与生态学", "水资源")],
        "weight": 4,
    },
    {
        "label": "stable isotopes",
        "aliases": ["同位素", "stable isotope", "stable isotopes", "isotope", "isotopic"],
        "categories": [("地球科学", "地球化学与地球物理")],
        "weight": 4,
    },
    {
        "label": "water quality",
        "aliases": ["水质", "water quality", "nitrate", "硝酸盐", "污染", "pollution", "contamination"],
        "categories": [("环境科学与生态学", "水资源"), ("环境科学与生态学", "环境科学")],
        "weight": 3,
    },
    {
        "label": "geochemistry",
        "aliases": ["地球化学", "geochemistry", "geochemical"],
        "categories": [("地球科学", "地球化学与地球物理")],
        "weight": 4,
    },
    {
        "label": "geology",
        "aliases": ["地质", "geology", "geological"],
        "categories": [("地球科学", "地质学")],
        "weight": 3,
    },
    {
        "label": "remote sensing",
        "aliases": ["遥感", "remote sensing", "satellite", "modis", "landsat", "sentinel"],
        "categories": [("地球科学", "遥感")],
        "weight": 4,
    },
    {
        "label": "atmosphere",
        "aliases": ["气象", "大气", "climate", "meteorology", "atmospheric", "precipitation"],
        "categories": [("地球科学", "气象与大气科学")],
        "weight": 3,
    },
    {
        "label": "soil",
        "aliases": ["土壤", "soil", "salinity", "盐碱"],
        "categories": [("环境科学与生态学", "土壤科学"), ("农林科学", "土壤科学")],
        "weight": 3,
    },
    {
        "label": "ecology",
        "aliases": ["生态", "ecology", "ecosystem", "biodiversity"],
        "categories": [("环境科学与生态学", "生态学")],
        "weight": 3,
    },
    {
        "label": "environmental science",
        "aliases": ["环境", "environment", "environmental"],
        "categories": [("环境科学与生态学", "环境科学")],
        "weight": 2,
    },
    {
        "label": "machine learning",
        "aliases": ["机器学习", "machine learning", "deep learning", "neural network", "人工智能", "ai"],
        "categories": [("计算机科学", "计算机：人工智能")],
        "weight": 1,
    },
    {
        "label": "gis",
        "aliases": ["gis", "geographic information system", "spatial analysis", "spatial", "mapping", "制图", "空间", "时空"],
        "categories": [("计算机科学", "计算机：跨学科应用"), ("地球科学", "遥感")],
        "weight": 3,
    },
    {
        "label": "oncology",
        "aliases": ["肿瘤", "癌", "cancer", "tumor", "tumour", "carcinoma", "oncology"],
        "categories": [("医学", "肿瘤学")],
        "weight": 4,
    },
    {
        "label": "medical imaging",
        "aliases": ["ct", "mri", "radiomics", "imaging", "医学影像", "放射组学"],
        "categories": [("医学", "成像科学与照相技术")],
        "weight": 3,
    },
    {
        "label": "medicine",
        "aliases": ["clinical", "patient", "disease", "therapy", "treatment", "医学", "临床"],
        "categories": [("医学", "医学：研究与实验")],
        "weight": 2,
    },
    {
        "label": "agriculture",
        "aliases": ["农业", "agriculture", "crop", "irrigation", "farmland"],
        "categories": [("农林科学", "农业综合")],
        "weight": 2,
    },
]


METHOD_RULES: List[Tuple[str, List[str]]] = [
    ("machine learning", ["machine learning", "deep learning", "random forest", "neural network", "机器学习", "深度学习"]),
    ("isotope tracing", ["stable isotope", "isotopic", "同位素"]),
    ("field experiment", ["field experiment", "sampling", "monitoring", "野外", "采样", "监测"]),
    ("modeling", ["model", "simulation", "模型", "模拟"]),
    ("review", ["review", "meta-analysis", "综述"]),
]


def infer_paper_profile(text: str, max_categories: int = 4) -> Dict:
    """Infer a compact paper profile from title, abstract, keywords, or full text."""
    normalized = _normalize_text(text)
    category_scores: Dict[Tuple[str, str], int] = {}
    matched_terms: List[str] = []

    for rule in TERM_RULES:
        hits = [alias for alias in rule["aliases"] if _contains_term(normalized, alias)]
        if not hits:
            continue

        matched_terms.append(rule["label"])
        for category in rule["categories"]:
            category_scores[category] = category_scores.get(category, 0) + rule["weight"]

    if not category_scores:
        category_scores[("综合性期刊", "")] = 1

    ranked_categories = sorted(category_scores.items(), key=lambda item: -item[1])
    categories = [
        {"category1": cat1, "category2": cat2, "score": score}
        for (cat1, cat2), score in ranked_categories[:max_categories]
    ]

    methods = []
    for method, aliases in METHOD_RULES:
        if any(_contains_term(normalized, alias) for alias in aliases):
            methods.append(method)

    return {
        "categories": categories,
        "matched_terms": matched_terms,
        "methods": methods,
        "input_length": len(text or ""),
    }


def search_candidates(
    categories: List[Category],
    impact_low: str = "",
    impact_high: str = "",
    sci_type: str = "",  # 默认不限 SCI 类型，包含 ESCI
    oa: str = "",
    partition: str = "",
    sort: str = "impactor",
    limit_per_category: int = 15,  # 每类取 15 个，扩大覆盖
) -> List[MetricRecord]:
    """Search LetPub candidates for multiple inferred categories.
    Covers all publishers, not limited to the 5 Journal Finder publishers."""
    grouped_candidates: List[List[MetricRecord]] = []

    for category in categories:
        parsed = advanced_search(
            searchcategory1=category.get("category1", ""),
            searchcategory2=category.get("category2", ""),
            searchimpactlow=impact_low,
            searchimpacthigh=impact_high,
            searchscitype=sci_type,
            searchopenaccess=oa,
            searchjcrkind=partition,
            searchsort=sort,
        )
        category_hits = []
        for journal in parsed.get("journals", []):
            name = journal.get("name", "")
            if name:
                item = dict(journal)
                item["_search_category"] = {
                    "category1": category.get("category1", ""),
                    "category2": category.get("category2", ""),
                }
                category_hits.append(item)

        grouped_candidates.append(category_hits[:limit_per_category])
        time.sleep(0.5)

    return interleave_candidate_groups(
        grouped_candidates,
        limit=max(1, limit_per_category) * max(1, len(categories)),
    )


def interleave_candidate_groups(groups: List[List[MetricRecord]], limit: int) -> List[MetricRecord]:
    """Round-robin candidate groups so one broad category cannot fill the list."""
    results: List[MetricRecord] = []
    seen = set()
    max_len = max((len(group) for group in groups), default=0)

    for index in range(max_len):
        for group in groups:
            if index >= len(group):
                continue
            item = group[index]
            name = item.get("name", "")
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            results.append(item)
            if len(results) >= limit:
                return results

    return results


def select_journals(
    text: str,
    categories: Optional[List[Category]] = None,
    impact_low: str = "",
    impact_high: str = "",
    sci_type: str = "",  # 默认不限 SCI 类型，包含 ESCI
    oa: str = "",
    partition: str = "",
    sort: str = "impactor",
    max_candidates: int = 10,
) -> Dict:
    """Run the full sci-aiselect workflow."""
    profile = infer_paper_profile(text)
    if categories:
        profile["categories"] = categories
    candidate_pool = search_candidates(
        profile["categories"],
        impact_low=impact_low,
        impact_high=impact_high,
        sci_type=sci_type,
        oa=oa,
        partition=partition,
        sort=sort,
        limit_per_category=max(8, max_candidates // max(1, len(profile["categories"])) + 4),
    )
    candidates = select_balanced_candidates(candidate_pool, max_candidates)

    metric_records = []
    for candidate in candidates:
        name = candidate.get("name", "")
        metrics = get_journal_metrics(name)
        if not metrics.get("_sources"):
            metrics.update(
                {
                    "impact_factor": candidate.get("impact_factor"),
                    "partition": candidate.get("partition", ""),
                    "sci_type": candidate.get("sci_type", ""),
                    "field": candidate.get("field", ""),
                    "_sources": ["letpub-search"],
                }
            )
        metrics["_candidate"] = candidate
        metric_records.append(metrics)
        time.sleep(1)

    ranked = assign_submission_bands(rank_metric_records(profile, metric_records))

    return {"profile": profile, "results": ranked}


def select_balanced_candidates(candidates: List[MetricRecord], max_candidates: int) -> List[MetricRecord]:
    """Pick high, middle, and lower-difficulty candidates before costly enrichment."""
    buckets = {"high": [], "middle": [], "lower": []}
    for candidate in candidates:
        buckets[_candidate_level(candidate)].append(candidate)

    if max_candidates <= 3:
        targets = {"high": 1, "middle": 1, "lower": 1}
    else:
        targets = {
            "high": max(1, max_candidates // 3),
            "middle": max(1, max_candidates // 3),
            "lower": max(1, max_candidates // 4),
        }

    selected: List[MetricRecord] = []
    seen = set()
    for level in ("high", "middle", "lower"):
        for candidate in buckets[level][: targets[level]]:
            _append_unique_candidate(selected, seen, candidate)

    for candidate in candidates:
        if len(selected) >= max_candidates:
            break
        _append_unique_candidate(selected, seen, candidate)

    return selected[:max_candidates]


def _append_unique_candidate(selected: List[MetricRecord], seen: set, candidate: MetricRecord) -> None:
    name = candidate.get("name", "")
    key = name.lower()
    if name and key not in seen:
        seen.add(key)
        selected.append(candidate)


def _candidate_level(candidate: MetricRecord) -> str:
    impact = _float(candidate.get("impact_factor"))
    partition = str(candidate.get("partition", ""))
    if "1区" in partition:
        return "high"
    if "2区" in partition:
        return "middle"
    if "3区" in partition or "4区" in partition:
        return "lower"
    if impact >= 8:
        return "high"
    if impact >= 5:
        return "middle"
    return "lower"


def rank_metric_records(
    profile: Dict,
    records: Iterable[MetricRecord],
    preferences: Optional[Dict] = None,
) -> List[Dict]:
    """Score and tier already-fetched journal metric records."""
    preferences = preferences or {}
    ranked = []

    for record in records:
        entry = dict(record)
        fit_score, fit_reasons = _topic_fit(profile, entry)
        quality_score, quality_reasons = _quality_score(entry, preferences)
        risk_penalty, risk_reasons = _risk_penalty(profile, entry)
        total_score = fit_score + quality_score - risk_penalty

        entry["fit_score"] = fit_score
        entry["quality_score"] = quality_score
        entry["risk_penalty"] = risk_penalty
        entry["score"] = total_score
        entry["fit_reasons"] = fit_reasons
        entry["quality_reasons"] = quality_reasons
        entry["risk_reasons"] = risk_reasons
        entry["tier"] = _tier(entry)
        entry["data_notes"] = _data_notes(entry)
        entry["metrics_line"] = format_metrics_line(entry)
        ranked.append(entry)

    tier_order = {"推荐": 0, "备选": 1, "谨慎": 2, "不推荐": 3}
    ranked.sort(key=lambda item: (tier_order.get(item["tier"], 9), -item["score"], -_float(item.get("impact_factor"))))
    return ranked


def assign_submission_bands(ranked: List[Dict]) -> List[Dict]:
    """Assign practical submission bands: ambition, solid, safe, or cautious."""
    for item in ranked:
        item["submission_band"] = _submission_band(item)
    return ranked


def format_selection_report(
    profile: Dict,
    ranked: List[Dict],
    title: str = "",
) -> str:
    """Format a concise user-facing sci-aiselect report."""
    if not ranked:
        return "sci-aiselect 未找到合适候选期刊。建议放宽影响因子、分区或学科筛选条件。"
    ranked = assign_submission_bands(ranked)

    lines = []
    heading = "sci-aiselect 选刊建议"
    if title:
        heading += f"：{title}"
    lines.append(f"# {heading}")
    lines.append("")

    category_text = "；".join(
        f"{c['category1']}/{c['category2'] or '综合'}" for c in profile.get("categories", [])
    )
    if category_text:
        lines.append(f"**识别方向**：{category_text}")

    terms = "、".join(profile.get("matched_terms", [])[:8])
    if terms:
        lines.append(f"**命中主题**：{terms}")

    lines.append("**重要提示**：未提供全文质量评价时，以下结果只是选刊梯度，不代表稿件一定适合或能够命中高影响力期刊。建议同时保留冲刺、稳妥和保底选择。")

    lines.append("")
    lines.append(format_selection_matrix(profile, ranked))
    lines.append("")
    tier_icons = {"推荐": "推荐", "备选": "备选", "谨慎": "谨慎", "不推荐": "不推荐"}
    for idx, item in enumerate(ranked, 1):
        band = item.get("submission_band", "待定")
        lines.append(f"## {idx}. {item.get('name', '未知期刊')}｜{band}｜{tier_icons.get(item['tier'], item['tier'])}")
        lines.append(f"**指标**：{item.get('metrics_line') or format_metrics_line(item)}")
        if item.get("fit_reasons"):
            lines.append(f"**匹配理由**：{'；'.join(item['fit_reasons'][:3])}")
        if item.get("risk_reasons"):
            lines.append(f"**风险提醒**：{'；'.join(item['risk_reasons'])}")
        if item.get("data_notes"):
            lines.append(f"**数据说明**：{'；'.join(item['data_notes'])}")
        lines.append("")

    return "\n".join(lines).strip()


def format_selection_matrix(
    profile: Dict,
    ranked: List[Dict],
) -> str:
    """Format a compact Markdown decision matrix."""
    ranked = assign_submission_bands(ranked)
    lines = [
        "## 快速决策表",
        "",
        "| 期刊 | 建议 | 主题匹配 | 梯度 | IF | 分区 | 收录 | OA/APC | 审稿速度 | 数据状态 |",
        "|---|---|---:|---|---:|---|---|---|---|---|",
    ]

    for item in ranked:
        lines.append(
            "| {name} | {tier} | {fit} | {band} | {impact} | {partition} | {sci} | {oa} | {speed} | {data} |".format(
                name=_table_cell(item.get("name", "")),
                tier=item.get("tier", ""),
                fit=item.get("fit_score", 0),
                band=item.get("submission_band", "待定"),
                impact=item.get("impact_factor") or "-",
                partition=item.get("partition") or "-",
                sci=_format_sci_cell(item),
                oa=_format_oa_cell(item),
                speed=_table_cell(_short_speed(item.get("speed", ""))),
                data=_table_cell(_compact_data_status(item)),
            )
        )

    return "\n".join(lines)


def format_report(results: List[Dict], profile: Optional[Dict] = None, **kwargs) -> str:
    """Compatibility wrapper for older callers that expect format_report(results)."""
    return format_selection_report(profile or {"categories": []}, results, **kwargs)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _contains_term(normalized_text: str, alias: str) -> bool:
    alias = alias.lower()
    if re.search(r"[\u4e00-\u9fff]", alias):
        return alias in normalized_text
    pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def _topic_fit(profile: Dict, record: MetricRecord) -> Tuple[int, List[str]]:
    candidate = record.get("_candidate", {}) or {}
    search_category = candidate.get("_search_category", {}) or record.get("_search_category", {}) or {}
    fields = " ".join(
        str(record.get(key, ""))
        for key in ("field", "partition_detail", "name", "shortname")
    )
    fields = " ".join(
        [
            fields,
            str(candidate.get("field", "")),
            str(search_category.get("category1", "")),
            str(search_category.get("category2", "")),
        ]
    ).lower()
    score = 0
    reasons: List[str] = []

    for category in profile.get("categories", []):
        cat2 = category.get("category2", "")
        cat1 = category.get("category1", "")
        weight = int(category.get("score", 1))
        if cat2 and cat2.lower() in fields:
            score += 12 + weight * 2
            reasons.append(f"覆盖核心方向 {cat2}")
        elif cat1 and cat1.lower() in fields:
            score += 6 + weight
            reasons.append(f"覆盖大类方向 {cat1}")

    for term in profile.get("matched_terms", []):
        if term.lower() in fields:
            score += 4

    if not reasons and profile.get("categories"):
        score += 4
        reasons.append("主题相关性需要人工复核")

    return score, reasons


def _quality_score(record: MetricRecord, preferences: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    sci = _clean_sci(record.get("sci_type", ""))
    if "SCIE" in sci or "SSCI" in sci:
        score += 14
        reasons.append("SCIE/SSCI 收录")
    elif "ESCI" in sci:
        score += 5
        reasons.append("ESCI 收录")

    partition = str(record.get("partition", ""))
    if "1区" in partition:
        score += 18
        reasons.append("中科院1区")
    elif "2区" in partition:
        score += 13
        reasons.append("中科院2区")
    elif "3区" in partition:
        score += 7
    elif "4区" in partition:
        score += 3

    impact = _float(record.get("impact_factor"))
    if impact >= 8:
        score += 12
    elif impact >= 5:
        score += 9
    elif impact >= 3:
        score += 5
    elif impact > 0:
        score += 2

    h_index = _float(record.get("h_index"))
    if h_index >= 150:
        score += 6
    elif h_index >= 80:
        score += 4
    elif h_index >= 30:
        score += 2

    if preferences.get("oa_required") and not record.get("is_oa"):
        score -= 8
        reasons.append("不满足 OA 偏好")

    return score, reasons


def _risk_penalty(profile: Dict, record: MetricRecord) -> Tuple[int, List[str]]:
    penalty = 0
    reasons: List[str] = []

    if record.get("warning"):
        penalty += 60
        reasons.append("LetPub/中科院预警风险")

    sci = _clean_sci(record.get("sci_type", ""))
    if "ESCI" in sci:
        # ESCI 不应该无条件惩罚——如果 JCR 分区是 Q1/Q2，说明质量不差
        partition = str(record.get("partition", ""))
        if "1区" in partition or "2区" in partition:
            penalty += 0  # JCR Q1/Q2 的 ESCI 期刊不扣分
        else:
            penalty += 12
            reasons.append("ESCI 期刊，需确认是否满足投稿要求")
    elif not sci and "letpub" in record.get("_sources", []):
        penalty += 35
        reasons.append("未确认 SCI/SCIE 收录")

    if "4区" in str(record.get("partition", "")):
        penalty += 8
        reasons.append("分区偏低")

    if _looks_like_review_journal(record.get("name", "")) and "review" not in profile.get("methods", []):
        penalty += 20
        reasons.append("综述型期刊，当前稿件更像研究论文")

    return penalty, reasons


def _tier(entry: MetricRecord) -> str:
    if entry.get("warning"):
        return "不推荐"

    if any("综述型期刊" in reason for reason in entry.get("risk_reasons", [])):
        return "谨慎"

    sci = _clean_sci(entry.get("sci_type", ""))
    if "ESCI" in sci:
        return "谨慎"
    if not sci and "letpub" in entry.get("_sources", []):
        return "谨慎"

    if entry["score"] >= 50 and entry["fit_score"] >= 22:
        return "推荐"
    if entry["score"] >= 34 and entry["fit_score"] >= 14:
        return "备选"
    if entry["score"] >= 18:
        return "谨慎"
    return "不推荐"


def _submission_band(item: Dict) -> str:
    if item.get("tier") in ("不推荐", "谨慎"):
        return "谨慎"
    if item.get("warning"):
        return "谨慎"
    if any("综述型期刊" in reason for reason in item.get("risk_reasons", [])):
        return "谨慎"

    sci = _clean_sci(item.get("sci_type", ""))
    if "ESCI" in sci:
        return "谨慎"

    impact = _float(item.get("impact_factor"))
    partition = str(item.get("partition", ""))
    if "1区" in partition:
        return "冲刺"
    if "2区" in partition:
        return "稳妥"
    if "3区" in partition or "4区" in partition:
        return "保底"
    if impact >= 8:
        return "冲刺"
    if impact >= 5:
        return "稳妥"
    return "保底"


def _data_notes(record: MetricRecord) -> List[str]:
    notes: List[str] = []
    sources = set(record.get("_sources", []))
    errors = record.get("_source_errors", {}) or {}

    if "letpub" not in sources and "letpub-search" not in sources:
        notes.append("LetPub详情未获取")
    if "openalex" not in sources:
        notes.append("OpenAlex未获取")

    for source, error in errors.items():
        if source == "openalex" and "OpenAlex未获取" not in notes:
            notes.append("OpenAlex未获取")
        elif source == "letpub" and "LetPub详情未获取" not in notes:
            notes.append("LetPub详情未获取")
        if error and len(str(error)) <= 80:
            notes.append(f"{source}: {error}")

    return notes


def _format_sci_cell(item: Dict) -> str:
    sci = str(item.get("sci_type") or "").replace(" ", "")
    normalized = _clean_sci(sci)
    if "SCIE" in normalized:
        return "SCIE"
    if "SSCI" in normalized:
        return "SSCI"
    if "ESCI" in normalized:
        return "ESCI"
    return sci or "-"


def _format_oa_cell(item: Dict) -> str:
    if item.get("is_oa") is True:
        return f"OA(${item['apc_usd']})" if item.get("apc_usd") else "OA"
    if item.get("is_oa") is False:
        return "非OA"
    return "-"


def _short_speed(speed: str) -> str:
    speed = str(speed or "").split("；")[0].replace("网友分享经验：", "").strip()
    return speed if speed else "-"


def _compact_data_status(item: Dict) -> str:
    notes = []
    sources = set(item.get("_sources", []))
    if "letpub" in sources or "letpub-search" in sources:
        notes.append("LetPub")
    if "openalex" in sources:
        notes.append("OpenAlex")
    if not notes:
        notes.append("待复核")
    if item.get("data_notes"):
        missing = [n for n in item["data_notes"] if "未获取" in n or "未核验" in n]
        notes.extend(missing[:2])
    return " / ".join(dict.fromkeys(notes))


def _table_cell(value: str) -> str:
    return str(value or "-").replace("|", "/").replace("\n", " ")


def _clean_sci(value: str) -> str:
    return str(value or "").upper().replace(" ", "")


def _looks_like_review_journal(name: str) -> bool:
    text = str(name or "").lower()
    return (
        "review" in text
        or "reviews" in text
        or text.startswith("annual review")
        or "interdisciplinary reviews" in text
    )


def _float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    demo = select_journals(
        "Groundwater nitrate source identification using stable isotopes and hydrochemistry",
        impact_low="3",
        max_candidates=8,
    )
    print(format_selection_report(demo["profile"], demo["results"]))
