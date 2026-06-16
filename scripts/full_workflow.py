"""
sci-aiselect 完整工作流

功能：
1. 从 Word/PDF 提取标题和摘要
2. Journal Finder 初筛（5个出版社）
3. AI 匹配（结合 Journal Finder 结果作为权重参考）
4. 提供 10 个综合选择
5. 意向期刊学习和摘要润色
6. 不满意时重新匹配
"""
from __future__ import annotations

import sys
import os
import re
from typing import Dict, List, Optional, Tuple

# 添加 scripts 目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from journal_finders import search_all_journal_finders
from journal_metrics import get_journal_metrics, format_metrics_line
from letpub_client import advanced_search


# ============================================================
# 文件提取功能
# ============================================================

def extract_from_file(file_path: str) -> Tuple[str, str, List[str]]:
    """
    从 Word 或 PDF 文件中提取标题、摘要和关键词
    
    Args:
        file_path: 文件路径
    
    Returns:
        Tuple[str, str, List[str]]: (标题, 摘要, 关键词)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return _extract_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return _extract_from_word(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _extract_from_pdf(file_path: str) -> Tuple[str, str, List[str]]:
    """从 PDF 文件提取"""
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return _parse_paper_text(text)
    except ImportError:
        raise ImportError("需要安装 pymupdf: pip install pymupdf")


def _extract_from_word(file_path: str) -> Tuple[str, str, List[str]]:
    """从 Word 文件提取"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return _parse_paper_text(text)
    except ImportError:
        raise ImportError("需要安装 python-docx: pip install python-docx")


def _parse_paper_text(text: str) -> Tuple[str, str, List[str]]:
    """
    从论文文本中解析标题、摘要和关键词
    
    Args:
        text: 论文全文
    
    Returns:
        Tuple[str, str, List[str]]: (标题, 摘要, 关键词)
    """
    lines = text.strip().split('\n')
    
    title = ""
    abstract = ""
    keywords = []
    
    # 提取标题（通常是第一个非空行）
    for line in lines:
        line = line.strip()
        if line and len(line) > 10:
            title = line
            break
    
    # 提取摘要
    abstract_start = -1
    abstract_end = -1
    
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if 'abstract' in line_lower and len(line_lower) < 20:
            abstract_start = i + 1
        elif abstract_start > 0:
            if any(keyword in line_lower for keyword in ['keywords', 'key words', 'introduction', '1.', '1 ']):
                abstract_end = i
                break
    
    if abstract_start > 0:
        if abstract_end < 0:
            abstract_end = min(abstract_start + 30, len(lines))
        abstract = " ".join(lines[abstract_start:abstract_end]).strip()
    
    # 提取关键词
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if 'keywords' in line_lower or 'key words' in line_lower:
            # 提取关键词行
            keyword_text = line
            if ':' in keyword_text:
                keyword_text = keyword_text.split(':', 1)[1]
            elif '：' in keyword_text:
                keyword_text = keyword_text.split('：', 1)[1]
            
            # 分割关键词
            for sep in [',', ';', '，', '；', '·']:
                if sep in keyword_text:
                    keywords = [kw.strip() for kw in keyword_text.split(sep) if kw.strip()]
                    break
            
            if not keywords:
                keywords = [keyword_text.strip()]
            
            break
    
    return title, abstract, keywords


# ============================================================
# 论文特征推断
# ============================================================

def infer_paper_profile(text: str, max_categories: int = 4) -> Dict:
    """推断论文特征"""
    TERM_RULES = [
        {"label": "groundwater", "aliases": ["地下水", "groundwater", "aquifer"], "categories": [("环境科学与生态学", "水资源")], "weight": 4},
        {"label": "hydrology", "aliases": ["水文", "hydrology", "hydrological", "watershed", "catchment", "basin"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "glacial", "aliases": ["冰川", "glacial", "glacier", "ice"], "categories": [("地球科学", "自然地理学")], "weight": 4},
        {"label": "lake", "aliases": ["湖", "lake", "lacustrine"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "hazard", "aliases": ["灾害", "hazard", "risk", "disaster"], "categories": [("环境科学与生态学", "环境科学")], "weight": 3},
        {"label": "remote sensing", "aliases": ["遥感", "remote sensing", "satellite"], "categories": [("地球科学", "遥感")], "weight": 4},
        {"label": "climate change", "aliases": ["气候变化", "climate change", "global warming"], "categories": [("地球科学", "气象与大气科学")], "weight": 3},
        {"label": "himalaya", "aliases": ["喜马拉雅", "himalaya", "himalayan"], "categories": [("地球科学", "自然地理学")], "weight": 4},
        {"label": "geology", "aliases": ["地质", "geology", "geological"], "categories": [("地球科学", "地质学")], "weight": 3},
        {"label": "ecology", "aliases": ["生态", "ecology", "ecosystem"], "categories": [("环境科学与生态学", "生态学")], "weight": 3},
        {"label": "ocean", "aliases": ["海洋", "ocean", "marine"], "categories": [("地球科学", "海洋学")], "weight": 3},
        {"label": "atmosphere", "aliases": ["大气", "atmosphere", "atmospheric"], "categories": [("地球科学", "气象与大气科学")], "weight": 3},
        {"label": "water quality", "aliases": ["水质", "water quality", "pollution"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "sediment", "aliases": ["沉积", "sediment", "sedimentary"], "categories": [("地球科学", "地质学")], "weight": 3},
        {"label": "GIS", "aliases": ["GIS", "geographic information", "spatial analysis"], "categories": [("地球科学", "遥感")], "weight": 3},
    ]
    
    normalized = re.sub(r'\s+', ' ', (text or '').lower())
    category_scores = {}
    matched_terms = []
    
    for rule in TERM_RULES:
        hits = [alias for alias in rule["aliases"] if alias.lower() in normalized]
        if hits:
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
    
    return {
        "categories": categories,
        "matched_terms": matched_terms,
        "methods": [],
        "input_length": len(text or ""),
    }


# ============================================================
# 期刊指标获取和排序
# ============================================================

def get_journal_metrics_safe(name: str) -> Dict:
    """安全获取期刊指标"""
    try:
        metrics = get_journal_metrics(name)
        return metrics
    except Exception as e:
        return {
            'name': name,
            '_sources': [],
            '_source_errors': {'all': str(e)},
        }


def _infer_paper_tier_from_finders(finder_results: List[Dict], abstract: str = "") -> Dict:
    """
    从 Journal Finder 推断论文档次。

    核心原则：Journal Finder 的排序是创新性最可靠的信号。
    出版社的匹配算法综合了摘要的创新性、方法深度、研究范围等因素。
    如果所有出版社都把普通期刊排第一，说明论文的创新性不足以投顶刊。

    信号优先级：
    1. Journal Finder 共识（首要）— 出版社对论文质量的集体判断
    2. 摘要创新性分析（辅助）— 用于中等情况的进一步判断
    3. 文献检索验证（可选）— 对中等创新性的论文做深度验证
    """
    if not finder_results:
        return {"tier": "unknown", "confidence": 0, "top_journals": [], "tier_label": "未知"}

    # === 信号 1: Journal Finder 排序分析（首要信号）===
    by_source = {}
    for r in finder_results:
        src = r.get('source', '')
        if src and src not in by_source:
            by_source[src] = r

    top_journals = [(src, r['journal_name']) for src, r in by_source.items()]
    total = len(top_journals)

    # 期刊档次分类
    NATURE_TIER = {
        'nature', 'science', 'nature climate change', 'nature geoscience',
        'nature communications', 'nature sustainability', 'nature water',
        'nature ecology & evolution', 'nature energy', 'nature food',
    }
    HIGH_TIER = NATURE_TIER | {
        'communications earth & environment', 'earth\'s future',
        'geophysical research letters', 'water resources research',
        'journal of hydrology', 'global and planetary change',
        'earth surface processes and landforms', 'environmental research letters',
    }
    REGIONAL_KEYWORDS = [
        'regional', 'arctic', 'antarctic', 'alpine', 'inland waters',
        'river basin', 'physical geography', 'case study',
    ]

    nature_count = sum(1 for _, jn in top_journals if jn.lower() in NATURE_TIER)
    high_count = sum(1 for _, jn in top_journals if jn.lower() in HIGH_TIER)
    regional_count = sum(1 for _, jn in top_journals
                         if any(kw in jn.lower() for kw in REGIONAL_KEYWORDS))

    # === 信号 2: 摘要创新性分析（辅助信号）===
    innovation_score, innovation_details = _assess_innovation(abstract or "")

    # === 信号 3: 研究范围（信息性）===
    abstract_lower = (abstract or "").lower()
    scope_info = {
        "regional": any(m in abstract_lower for m in [
            "indian himalayan", "indian himalaya", "study area",
            "study region", "transboundary", "basin-scale",
        ]),
        "case_study": any(m in abstract_lower for m in [
            "case study", "case studies", "this study integrates",
        ]),
        "applied": any(m in abstract_lower for m in [
            "downstream hazard", "hydropower infrastructure",
            "risk assessment", "vulnerability",
        ]),
    }

    # === 综合判断论文档次 ===
    # 核心逻辑：Journal Finder 的共识是首要且决定性的判断依据
    # 摘要正则分析可靠性太低（既会高估也会漏判），仅用于微调
    #
    # 判断矩阵：
    # - 多数出版社 #1 是 Nature 级 → breakthrough
    # - 多数出版社 #1 是高影响力期刊 → high
    # - 多数出版社 #1 是区域/专业期刊 → solid（正则最多微调到 solid_high）
    # - 出版社分歧大 → 取中间值

    finder_majority_nature = nature_count >= max(2, total * 0.5)
    finder_majority_high = high_count >= max(2, total * 0.5)
    finder_majority_regional = regional_count >= max(2, total * 0.5)

    if finder_majority_nature:
        tier = "breakthrough"
        tier_label = "突破性研究"
    elif finder_majority_high and not finder_majority_regional:
        tier = "high"
        tier_label = "高质量研究"
    elif finder_majority_regional:
        # Journal Finder 明确说了：这是区域级研究
        # 正则创新性评分可靠性太低，不能推翻 Journal Finder 的判断
        # 但如果有非常强的创新信号（≥70），可以微调到 solid_high
        if innovation_score >= 70:
            tier = "solid_high"
            tier_label = "扎实偏高质量研究（创新性有亮点，建议文献检索验证）"
        else:
            tier = "solid"
            tier_label = "扎实研究"
    else:
        # 出版社分歧 → 取中间值，参考创新性
        # 如果创新性信号足够强（≥50），提升到 solid_high 以触发跨学科期刊池
        if innovation_score >= 50:
            tier = "solid_high"
            tier_label = "扎实偏高质量研究"
        else:
            tier = "solid"
            tier_label = "扎实研究"

    # 提取潜在创新点（供后续文献检索验证）
    innovation_points = _extract_innovation_points(abstract or "")

    return {
        "tier": tier,
        "tier_label": tier_label,
        "confidence": total,
        "top_journals": top_journals,
        "nature_count": nature_count,
        "high_count": high_count,
        "regional_count": regional_count,
        "innovation_score": innovation_score,
        "innovation_details": innovation_details,
        "scope_info": scope_info,
        "innovation_points": innovation_points,
        "needs_novelty_verification": tier in ("solid", "solid_high") and len(innovation_points) > 0,
    }


def _assess_innovation(abstract: str) -> Tuple[int, List[Dict]]:
    """
    评估摘要中的创新性（0-100 分）。

    只匹配真正的创新信号，不匹配论文涉及的主题或方法。
    "用了XX方法"不是创新，"第一次用XX方法发现了YY"才是创新。

    创新信号类型：
    1. 明确的创新声明 — "for the first time", "novel", "addresses this gap"
    2. 前所未有的发现 — "remarkably", "in stark contrast", "fundamental difference"
    3. 明确的方法突破 — "novel method/framework"（不是"用了XX方法"）

    此分数仅用于微调 Journal Finder 的判断。
    """
    abstract_lower = (abstract or "").lower()
    details = []
    score = 0

    # 已匹配的文本片段（防止同一段文字被多个模式重复匹配）
    _matched_spans: List[Tuple[int, int]] = []

    def _try_match(pattern, label, points, desc, category):
        nonlocal score
        m = re.search(pattern, abstract_lower)
        if not m:
            return
        start, end = m.start(), m.end()
        for ms, me in _matched_spans:
            if start < me and end > ms:
                return
        _matched_spans.append((start, end))
        score += points
        details.append({"type": category, "label": label, "points": points, "desc": desc})

    # 1. 明确的创新声明（最高 40 分）
    # 只匹配作者自己说"这是新的/第一次/填补空白"
    _try_match(
        r"(this study|we)\s+.{0,20}(for the first time|first to|are the first|首次)",
        "首次声明", 40, "作者明确声明首次研究", "claim")
    _try_match(
        r"(this study|we)\s+.{0,20}(addresses|fill|bridge)\s+.{0,10}(this|the|a)\s+(gap|void|shortcoming)",
        "填补空白声明", 35, "作者明确声明填补研究空白", "claim")
    _try_match(
        r"(novel|new|innovative)\s+(method|approach|framework|technique|model|tool)\s+.{0,20}(for|to|that|which)",
        "新方法声明", 30, "作者声明提出新方法", "claim")

    # 2. 前所未有的发现（最高 30 分）
    # 只匹配作者强调的反直觉或关键性发现
    _try_match(
        r"(remarkably|strikingly|in stark contrast|fundamentally different|crucial.{0,5}(differ|contrast))",
        "关键差异发现", 25, "作者强调的关键性差异或反直觉发现", "finding")
    _try_match(
        r"(robustly|clearly|unambiguously)\s+(detected|identified|observed)\s+.{0,20}(years? in advance|before|prior|precursor)",
        "前兆检测成功", 30, "成功提前多年检测到前兆信号", "finding")

    # 3. 系统性对比（最高 20 分）
    # 只匹配"对比了两种不同类型并发现了关键差异"
    _try_match(
        r"(contrasting|contrast)\s+.{0,15}(precursor|signal|detection|deformation|response)\s+.{0,15}(between|across|dependent|different)",
        "系统性对比发现", 20, "系统对比不同类型系统的关键差异", "finding")

    # 4. 显著的定量发现（最高 25 分）
    # 通过数据展现的创新——"5-fold increase"、"comparable to alpine glaciation"
    _try_match(
        r"(\d+)-?fold\s+(increase|decrease|change|rise|growth|reduction)",
        "倍数级变化", 25, "发现显著的倍数级变化趋势", "finding")
    _try_match(
        r"comparable\s+(to|with)\s+.{0,20}(glaciation|erosion|denudation|tectonic)",
        "可比自然过程", 20, "发现与重要自然过程可比的速率", "finding")
    _try_match(
        r"(migrat|shift|mov)\w+\s+.{0,20}(upslope|upward|poleward|higher elevation)",
        "空间迁移趋势", 20, "发现灾害/过程的空间迁移趋势", "finding")
    _try_match(
        r"(we|this study)\s+.{0,15}(identify|reveal|discover|demonstrate)\s+.{0,15}(\d+)-?fold",
        "倍数发现声明", 20, "作者声明发现显著倍数变化", "finding")

    # 封顶 100
    score = min(score, 100)

    return score, details


def _extract_innovation_points(abstract: str) -> List[Dict]:
    """
    从摘要中提取可能的创新点，用于后续文献检索验证。
    返回创新点列表，每个包含：类型、关键词、原文片段。
    """
    abstract_lower = abstract.lower()
    points = []

    # 1. 方法创新：新的数据源组合或分析方法
    METHOD_PATTERNS = [
        (r"integrat\w+\s+.{0,30}(satellite|remote sensing|observation)", "方法整合", "multi-source integration"),
        (r"(multi-decadal|long.term|multi.temporal)", "时间尺度", "multi-decadal analysis"),
        (r"(compound|cascad\w+|multi.hazard)", "复合灾害", "compound hazard"),
        (r"(machine learning|deep learning|ai|neural)", "AI方法", "machine learning approach"),
        (r"(novel|new|innovative)\s+(method|approach|framework|technique)", "方法创新", "novel methodology"),
    ]
    for pattern, label, search_term in METHOD_PATTERNS:
        if re.search(pattern, abstract_lower):
            match = re.search(pattern, abstract_lower)
            points.append({
                "type": "method",
                "label": label,
                "search_term": search_term,
                "context": match.group(0) if match else "",
            })

    # 2. 范围创新：覆盖范围或数据规模
    SCOPE_PATTERNS = [
        (r"(\d+)\s+(potentially dangerous|dangerous|glacial)\s+lake", "大规模调查", "systematic glacial lake assessment"),
        (r"(first|comprehensive|systematic)\s+(assessment|inventory|analysis|survey)", "首次/系统性评估", "comprehensive assessment"),
        (r"(transboundary|cross.border|multi.country)", "跨境研究", "transboundary analysis"),
        (r"(indian himalayan|specific region)\s+region", "区域覆盖", "Indian Himalayan Region"),
    ]
    for pattern, label, search_term in SCOPE_PATTERNS:
        if re.search(pattern, abstract_lower):
            match = re.search(pattern, abstract_lower)
            points.append({
                "type": "scope",
                "label": label,
                "search_term": search_term,
                "context": match.group(0) if match else "",
            })

    # 3. 发现创新：非显而易见的发现
    FINDING_PATTERNS = [
        (r"(non.linear|accelerated|unexpected|surprising)", "非线性/意外发现", "non-linear glacial lake change"),
        (r"(sediment|debris|moraine).{0,20}(process|dynamic|interaction)", "泥沙过程", "sediment process glacial lake"),
        (r"(hydropower|infrastructure).{0,20}(vulnerab|risk|expos)", "基础设施风险", "hydropower GLOF vulnerability"),
    ]
    for pattern, label, search_term in FINDING_PATTERNS:
        if re.search(pattern, abstract_lower):
            match = re.search(pattern, abstract_lower)
            points.append({
                "type": "finding",
                "label": label,
                "search_term": search_term,
                "context": match.group(0) if match else "",
            })

    return points


def rank_metric_records(profile: Dict, records: List[Dict], finder_results: List[Dict] = None, abstract: str = "") -> List[Dict]:
    """
    评分和排序期刊记录。

    核心改进：先从 Journal Finder 的整体排序推断论文档次，
    再用论文档次校准 quality_score，防止区域研究被推荐到 Nature 子刊。

    Args:
        profile: 论文特征
        records: 期刊指标记录
        finder_results: Journal Finder 结果（用于权重参考 + 档次推断）
        abstract: 论文摘要文本（用于范围信号检测）
    """
    # === Step 0: 推断论文档次 ===
    paper_tier_info = _infer_paper_tier_from_finders(finder_results or [], abstract=abstract)
    paper_tier = paper_tier_info["tier"]

    # 论文档次对 quality_score 的缩放因子
    # 核心原则：创新性决定天花板，范围不决定天花板
    # solid_high = 扎实偏高，保留一定质量加分
    TIER_QUALITY_SCALE = {
        "breakthrough": 1.0,   # 顶刊论文：quality_score 全额计算
        "high": 0.95,          # 高质量研究：几乎全额
        "solid_high": 0.85,    # 扎实偏高：适度压缩
        "solid": 0.7,          # 扎实研究：中等压缩
        "unknown": 0.8,        # 未知：保守处理
    }
    tier_scale = TIER_QUALITY_SCALE.get(paper_tier, 0.8)

    # 创建 Journal Finder 结果的查找表（保留所有来源的排名信息）
    finder_lookup = {}
    finder_rank_lookup = {}  # 期刊在各来源中的排名
    if finder_results:
        for r in finder_results:
            name_lower = r['journal_name'].lower()
            if name_lower not in finder_lookup:
                finder_lookup[name_lower] = r
            # 记录排名（position 越小越好）
            if name_lower not in finder_rank_lookup:
                finder_rank_lookup[name_lower] = []
            finder_rank_lookup[name_lower].append({
                'source': r.get('source', ''),
                'position': r.get('position', 99),
                'match_score': r.get('match_score', 0),
            })

    # 统计多少个出版社推荐了某期刊（共识度）
    finder_consensus = {}
    for name_lower, sources in finder_rank_lookup.items():
        finder_consensus[name_lower] = len(sources)

    ranked = []

    for record in records:
        entry = dict(record)
        name = entry.get('name', '')
        name_lower = name.lower()

        # 计算 fit_score
        fit_score = 0

        # 1. 基于 Journal Finder 结果的权重（考虑共识度）
        if name_lower in finder_lookup:
            finder_score = finder_lookup[name_lower].get('match_score', 0)
            consensus = finder_consensus.get(name_lower, 1)
            # 共识度加权：1个出版社 = 基础分，多个出版社 = 额外加分
            consensus_bonus = min(consensus - 1, 4) * 3  # 每多1个出版社 +3，上限 +12
            fit_score += finder_score * 20 + consensus_bonus  # 最高 32 分（降低权重，防止 finder 压过主题匹配）

        # 2. 基于主题匹配
        matched_terms = profile.get('matched_terms', [])
        field = str(entry.get('field', '')).lower()
        for term in matched_terms:
            if term.lower() in field:
                fit_score += 5

        # 3. 基于分类匹配
        for category in profile.get('categories', []):
            cat1 = category.get('category1', '').lower()
            cat2 = category.get('category2', '').lower()
            if cat1 in field or cat2 in field:
                fit_score += 10

        # 计算 quality_score（受论文档次缩放）
        # 原理：区域研究的 quality_score 被压缩，防止高 IF 期刊凭借指标优势压过主题匹配
        raw_quality_score = 0
        impact_factor = float(entry.get('impact_factor', 0) or 0)
        partition = str(entry.get('partition', ''))

        if '1区' in partition:
            raw_quality_score += 18
        elif '2区' in partition:
            raw_quality_score += 13
        elif '3区' in partition:
            raw_quality_score += 7
        elif '4区' in partition:
            raw_quality_score += 3

        if impact_factor >= 20:
            raw_quality_score += 15
        elif impact_factor >= 10:
            raw_quality_score += 12
        elif impact_factor >= 5:
            raw_quality_score += 9
        elif impact_factor >= 3:
            raw_quality_score += 5
        elif impact_factor > 0:
            raw_quality_score += 2

        h_index = float(entry.get('h_index', 0) or 0)
        if h_index >= 200:
            raw_quality_score += 8
        elif h_index >= 100:
            raw_quality_score += 5
        elif h_index >= 50:
            raw_quality_score += 3

        # 应用论文档次缩放
        quality_score = int(raw_quality_score * tier_scale)

        # 计算 risk_penalty
        risk_penalty = 0
        if entry.get('warning'):
            risk_penalty += 60

        sci = str(entry.get('sci_type', '')).upper()
        if 'ESCI' in sci:
            # ESCI 不应该无条件惩罚——如果 JCR 分区是 Q1/Q2，说明质量不差
            if '1区' in partition or '2区' in partition:
                risk_penalty += 0  # JCR Q1/Q2 的 ESCI 期刊不扣分
            else:
                risk_penalty += 10  # 没有好的分区数据才扣分
        elif not sci and 'letpub' in entry.get('_sources', []):
            risk_penalty += 30

        # aim & scope 语义匹配加分
        # 将论文标题/摘要中的关键词与期刊名/领域做交叉匹配
        aim_scope_bonus = 0
        paper_text = (profile.get('_title', '') + ' ' + profile.get('_abstract', '')).lower()
        journal_name_lower = name.lower()
        journal_field_lower = field.lower()

        # 从论文文本中提取有意义的关键词（去掉常见停用词）
        PAPER_KEYWORDS = {
            'indicators': '指标',
            'recovery': '恢复',
            'inequality': '不平等',
            'flood': '洪水',
            'disaster': '灾害',
            'sustainability': '可持续',
            'sustainable': '可持续',
            'resilience': '韧性',
            'vulnerability': '脆弱性',
            'risk': '风险',
            'hazard': '危害',
            'remote sensing': '遥感',
            'satellite': '卫星',
            'hydrolog': '水文',
            'climate': '气候',
            'ecology': '生态',
            'environment': '环境',
            'policy': '政策',
            'management': '管理',
        }

        for keyword in PAPER_KEYWORDS:
            if keyword in paper_text:
                # 如果论文关键词也出现在期刊名或领域中，加分
                if keyword in journal_name_lower or keyword in journal_field_lower:
                    aim_scope_bonus += 8  # 每项 8 分（提高权重，让主题匹配能压过 IF 排序）

        # 封顶 30 分
        aim_scope_bonus = min(aim_scope_bonus, 30)

        # 总分
        total_score = fit_score + quality_score - risk_penalty + aim_scope_bonus

        entry['fit_score'] = fit_score
        entry['quality_score'] = quality_score
        entry['raw_quality_score'] = raw_quality_score
        entry['risk_penalty'] = risk_penalty
        entry['aim_scope_bonus'] = aim_scope_bonus
        entry['score'] = total_score
        entry['metrics_line'] = format_metrics_line(entry)
        entry['_paper_tier'] = paper_tier_info

        # 来源信息
        sources = []
        if name_lower in finder_lookup:
            sources.append(f"journal_finder: {finder_lookup[name_lower].get('source', '')}")
        if entry.get('_sources'):
            sources.extend(entry['_sources'])
        entry['data_sources'] = sources

        # 确定 tier（阈值适配缩放后的 quality_score）
        if entry.get('warning'):
            entry['tier'] = '不推荐'
        elif total_score >= 40 and fit_score >= 15:
            entry['tier'] = '推荐'
        elif total_score >= 28 and fit_score >= 10:
            entry['tier'] = '备选'
        elif total_score >= 16:
            entry['tier'] = '谨慎'
        else:
            entry['tier'] = '不推荐'

        ranked.append(entry)

    # 排序
    tier_order = {"推荐": 0, "备选": 1, "谨慎": 2, "不推荐": 3}
    ranked.sort(key=lambda item: (tier_order.get(item["tier"], 9), -item["score"]))

    return ranked


def assign_submission_bands(ranked: List[Dict]) -> List[Dict]:
    """分配投稿梯度（基于创新性推断的论文档次，而非研究范围）"""
    # 从第一条记录获取论文档次
    paper_tier = "unknown"
    if ranked and ranked[0].get('_paper_tier'):
        paper_tier = ranked[0]['_paper_tier'].get('tier', 'unknown')

    # 论文档次对投稿梯度的天花板
    # 核心原则：创新性决定天花板，范围不决定天花板
    TIER_BAND_CAP = {
        "breakthrough": "冲刺",    # 突破性研究：不限制
        "high": "冲刺",            # 高质量研究：不限制
        "solid_high": "稳妥",      # 扎实偏高：最高"稳妥"
        "solid": "稳妥",           # 扎实研究：最高"稳妥"
        "unknown": "冲刺",         # 未知：不限制
    }
    band_cap = TIER_BAND_CAP.get(paper_tier, "冲刺")

    for item in ranked:
        if item.get("tier") in ("不推荐", "谨慎"):
            item["submission_band"] = "谨慎"
        elif item.get("warning"):
            item["submission_band"] = "谨慎"
        else:
            partition = str(item.get("partition", ""))
            impact = float(item.get("impact_factor", 0) or 0)

            if "1区" in partition or impact >= 10:
                band = "冲刺"
            elif "2区" in partition or impact >= 5:
                band = "稳妥"
            else:
                band = "保底"

            # 应用论文档次天花板
            if band_cap == "稳妥" and band == "冲刺":
                band = "稳妥"

            item["submission_band"] = band

    return ranked


# ============================================================
# 格式化输出
# ============================================================

def format_selection_matrix(profile: Dict, ranked: List[Dict]) -> str:
    """格式化决策表"""
    lines = [
        "## 快速决策表",
        "",
        "| 期刊 | 建议 | 梯度 | IF | 分区 | 收录 |",
        "|---|---|---|---:|---|---|",
    ]
    
    for item in ranked:
        name = str(item.get('name', '-')).replace('|', '/').replace('\n', ' ')
        if len(name) > 40:
            name = name[:37] + "..."
        tier = item.get('tier', '')
        band = item.get('submission_band', '待定')
        impact = item.get('impact_factor') or '-'
        partition = item.get('partition') or '-'
        sci = item.get('sci_type') or '-'
        
        lines.append(f"| {name} | {tier} | {band} | {impact} | {partition} | {sci} |")
    
    return "\n".join(lines)


def format_full_report(
    bundle: Dict,
    title: str = "",
    show_finder_results: bool = True,
) -> str:
    """生成完整的报告"""
    lines = []
    
    # 标题
    if title:
        lines.append(f"# sci-aiselect 选刊建议：{title}")
    else:
        lines.append("# sci-aiselect 选刊建议")
    lines.append("")
    
    # Journal Finder 结果
    if show_finder_results and bundle.get('finder_results'):
        lines.append("## Journal Finder 初筛结果")
        lines.append("")
        
        by_source = {}
        for r in bundle['finder_results']:
            source = r['source']
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(r)
        
        for source, journals in by_source.items():
            lines.append(f"### {source}")
            for i, j in enumerate(journals[:10], 1):
                lines.append(f"{i}. {j['journal_name']} (匹配度: {j['match_score']:.2f})")
            lines.append("")
    
    # AI 匹配结果
    lines.append("## AI 智能匹配结果")
    lines.append("")
    
    profile = bundle.get('profile', {})
    category_text = "；".join(
        f"{c['category1']}/{c['category2'] or '综合'}" for c in profile.get("categories", [])
    )
    if category_text:
        lines.append(f"**识别方向**：{category_text}")
    
    terms = "、".join(profile.get("matched_terms", [])[:8])
    if terms:
        lines.append(f"**命中主题**：{terms}")

    # 论文档次推断（基于 Journal Finder 整体排序）
    paper_tier_info = None
    if bundle.get('results') and bundle['results'][0].get('_paper_tier'):
        paper_tier_info = bundle['results'][0]['_paper_tier']
    if not paper_tier_info and bundle.get('paper_tier_info'):
        paper_tier_info = bundle['paper_tier_info']

    if paper_tier_info and paper_tier_info.get('tier') != 'unknown':
        tier_label = paper_tier_info.get('tier_label', paper_tier_info['tier'])
        top_names = [jname for _, jname in paper_tier_info.get('top_journals', [])][:3]
        top_str = "、".join(top_names) if top_names else "无"
        lines.append(f"**论文档次**：{tier_label}（各出版社 #1 推荐：{top_str}）")

        # 显示创新性评分
        innovation_score = paper_tier_info.get('innovation_score', 0)
        innovation_details = paper_tier_info.get('innovation_details', [])
        if innovation_score > 0:
            lines.append(f"**创新性评分**：{innovation_score}/100")
            for d in innovation_details:
                lines.append(f"  - 【{d['label']}】+{d['points']}分 — {d['desc']}")

        # 显示研究范围（信息性）
        scope_info = paper_tier_info.get('scope_info', {})
        scope_labels = []
        if scope_info.get('regional'):
            scope_labels.append("区域聚焦")
        if scope_info.get('case_study'):
            scope_labels.append("案例研究")
        if scope_info.get('applied'):
            scope_labels.append("应用导向")
        if scope_labels:
            lines.append(f"**研究范围**：{'、'.join(scope_labels)}（仅作参考，不影响档次判断）")

        # 显示创新点（供文献检索验证）
        innovation_points = paper_tier_info.get('innovation_points', [])
        if innovation_points:
            lines.append("")
            lines.append("**潜在创新点**（待文献检索验证）：")
            for ip in innovation_points:
                lines.append(f"- 【{ip['label']}】{ip['context']} → 检索词：`{ip['search_term']}`")

        # 如果需要创新验证，输出提示
        if paper_tier_info.get('needs_novelty_verification'):
            lines.append("")
            lines.append("> ⚠️ **创新性评分中等，建议对上述创新点进行文献检索验证。**")
            lines.append("> 如果验证发现创新点确实新颖，可提升论文档次。")

    lines.append("")
    
    # 决策表
    lines.append(format_selection_matrix(profile, bundle['results']))
    lines.append("")
    
    # 详细推荐
    tier_icons = {"推荐": "推荐", "备选": "备选", "谨慎": "谨慎", "不推荐": "不推荐"}
    for idx, item in enumerate(bundle['results'], 1):
        band = item.get("submission_band", "待定")
        lines.append(f"## {idx}. {item.get('name', '未知期刊')}｜{band}｜{tier_icons.get(item['tier'], item['tier'])}")
        lines.append(f"**指标**：{item.get('metrics_line') or format_metrics_line(item)}")
        
        # 来源信息
        source_info = []
        if item.get('data_sources'):
            source_info.append(f"来源: {', '.join(item['data_sources'])}")
        if source_info:
            lines.append(f"**来源**：{'；'.join(source_info)}")
        
        lines.append("")
    
    return "\n".join(lines).strip()


# ============================================================
# 主工作流
# ============================================================

def select_journals_with_finder(
    title: str,
    abstract: str,
    keywords: List[str] = None,
    use_journal_finders: bool = True,
    finder_config: Dict = None,
    impact_low: str = "3",
    max_candidates: int = 10,
) -> Dict:
    """
    完整的期刊选择流程
    
    Args:
        title: 论文标题
        abstract: 论文摘要
        keywords: 关键词列表
        use_journal_finders: 是否使用 Journal Finder 初筛
        finder_config: Journal Finder 配置
        impact_low: 最低影响因子
        max_candidates: 最大候选数量
    
    Returns:
        Dict: 包含 profile, results, finder_results
    """
    # 构建论文文本
    paper_text = title + "\n" + abstract
    if keywords:
        paper_text += "\n关键词：" + ", ".join(keywords)
    
    # 步骤 1: Journal Finder 初筛
    finder_results = []
    if use_journal_finders:
        print("\n" + "="*70)
        print("步骤 1: Journal Finder 初筛")
        print("="*70)
        
        default_config = {
            'timeout': 90000,
            'retry_count': 1,
            'elsevier': {'enabled': True},
            'wiley': {'enabled': True},
            'taylor_francis': {'enabled': True},
            'springer': {'enabled': True},
            'wos': {'enabled': True},
        }
        
        if finder_config:
            default_config.update(finder_config)
        
        finder_results = search_all_journal_finders(title, abstract, keywords, default_config)
        
        print(f"\nJournal Finder 共找到 {len(finder_results)} 个期刊")
        
        # 按来源分组显示
        by_source = {}
        for r in finder_results:
            source = r['source']
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(r)
        
        for source, journals in by_source.items():
            print(f"\n{source}: {len(journals)} 个期刊")
            for j in journals[:5]:
                print(f"  - {j['journal_name']} (匹配度: {j['match_score']:.2f})")
    
    # 步骤 2: AI 智能匹配
    print("\n" + "="*70)
    print("步骤 2: AI 智能匹配")
    print("="*70)
    
    # 推断论文特征
    profile = infer_paper_profile(paper_text)
    profile['_title'] = title or ''
    profile['_abstract'] = abstract or ''
    
    print("\n论文特征:")
    category_text = ", ".join([c["category1"] + "/" + c["category2"] for c in profile['categories']])
    print("  识别方向: " + category_text)
    print("  命中主题: " + ", ".join(profile['matched_terms']))

    # 从 Journal Finder 结果推断论文档次
    paper_tier_info = _infer_paper_tier_from_finders(finder_results, abstract=abstract)
    if paper_tier_info['tier'] != 'unknown':
        print(f"  论文档次: {paper_tier_info['tier_label']}")
        print(f"  创新性评分: {paper_tier_info.get('innovation_score', 0)}/100")
        for d in paper_tier_info.get('innovation_details', []):
            print(f"    + {d['label']} ({d['points']}分): {d['desc']}")
        top_names = [jname for _, jname in paper_tier_info.get('top_journals', [])][:3]
        print(f"  各出版社 #1: {', '.join(top_names)}")

    # 获取 Journal Finder 期刊的指标
    print("\n正在获取期刊指标...")
    metric_records = []
    
    # 收集所有候选期刊名称
    candidate_names = set()

    # 1. Journal Finder 结果
    for finder_result in finder_results:
        candidate_names.add(finder_result['journal_name'])

    # 2. 跨学科顶级期刊（永远不在 Journal Finder 或 LetPub 分类搜索中出现）
    # 这些期刊发表高质量的跨学科地球/气候/环境科学研究
    # 当论文档次为 high 或 breakthrough 时，必须考虑
    TOP_TIER_CROSS_DISCIPLINARY = {
        'National Science Review',
        'Nature',
        'Science',
        'PNAS',
        'Nature Communications',
        'Nature Geoscience',
        'Nature Climate Change',
        'Nature Sustainability',
        'Nature Water',
        'Nature Earth and Environment',
        'Science Advances',
        'Proceedings of the National Academy of Sciences',
    }
    # 如果论文档次是 high 或 breakthrough，加入跨学科顶级期刊
    if paper_tier_info.get('tier') in ('breakthrough', 'high', 'solid_high'):
        for jname in TOP_TIER_CROSS_DISCIPLINARY:
            candidate_names.add(jname)
        print(f"  跨学科顶级期刊: 已加入 {len(TOP_TIER_CROSS_DISCIPLINARY)} 个候选")

    # 3. 基于 LetPub 搜索的候选（扩展覆盖范围，不限于 5 个出版社）
    # LetPub 覆盖所有出版社的期刊，是 Journal Finder 的重要补充
    print("正在搜索 LetPub 候选期刊...")
    for category in profile['categories'][:4]:
        try:
            # 不限 SCI 类型——ESCI 期刊如果 JCR Q1/Q2 也是好选择
            results = advanced_search(
                searchcategory1=category.get('category1', ''),
                searchcategory2=category.get('category2', ''),
                searchimpactlow=impact_low,
                searchscitype='',  # 不限 SCI 类型，包含 ESCI
                searchsort='impactor',
            )
            for journal in results.get('journals', [])[:15]:  # 每类取 15 个
                name = journal.get('name', '')
                if name:
                    candidate_names.add(name)
        except Exception as e:
            print(f"  LetPub 搜索失败: {e}")
    
    # 获取所有候选期刊的指标
    print(f"\n正在获取 {len(candidate_names)} 个候选期刊的指标...")
    for name in candidate_names:
        metrics = get_journal_metrics_safe(name)
        if metrics.get('_sources'):
            metric_records.append(metrics)
    
    # 排序和分带
    print("\n正在进行智能排序...")
    ranked = assign_submission_bands(rank_metric_records(profile, metric_records, finder_results, abstract=abstract))
    
    # 限制结果数量
    ranked = ranked[:max_candidates]
    
    return {
        'profile': profile,
        'results': ranked,
        'finder_results': finder_results,
        'paper_tier_info': ranked[0].get('_paper_tier') if ranked else None,
    }


# ============================================================
# 便捷函数
# ============================================================

def quick_select(title: str, abstract: str, keywords: List[str] = None) -> str:
    """快速选刊"""
    bundle = select_journals_with_finder(title, abstract, keywords)
    return format_full_report(bundle, title=title)


def extract_and_select(file_path: str) -> str:
    """
    从文件提取并选刊
    
    Args:
        file_path: Word 或 PDF 文件路径
    
    Returns:
        str: 格式化的报告
    """
    title, abstract, keywords = extract_from_file(file_path)
    
    print(f"提取的标题: {title[:50]}...")
    print(f"提取的摘要: {abstract[:100]}...")
    print(f"提取的关键词: {keywords}")
    
    bundle = select_journals_with_finder(title, abstract, keywords)
    return format_full_report(bundle, title=title)
