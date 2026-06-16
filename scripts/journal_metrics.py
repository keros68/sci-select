"""
多源期刊指标聚合器
数据源：LetPub（IF/分区/审稿速度/SCI收录）+ OpenAlex（h-index/OA/APC）
使用公开页面和 OpenAlex 获取基础指标
"""
import requests
import time
import json
import os
import re
from typing import Dict, Optional, List

try:
    from .letpub_client import lookup_journal
except ImportError:
    from letpub_client import lookup_journal

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
CACHE_FILE = os.path.join(CACHE_DIR, 'journal_cache.json')
CACHE_TTL = 7 * 86400  # 7天


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get_letpub_info(journal_name: str) -> Optional[Dict]:
    """从 LetPub 获取期刊详情"""
    try:
        return lookup_journal(journal_name)
    except Exception as e:
        print(f"LetPub 查询失败 [{journal_name}]: {e}")
        return None


def _get_openalex_info(journal_name: str, issn: str = None) -> Optional[Dict]:
    """从 OpenAlex 获取期刊指标"""
    try:
        # 优先用 ISSN 搜索（更精确）
        if issn:
            url = f"https://api.openalex.org/sources?filter=issn:{issn}&per_page=1"
        else:
            url = f"https://api.openalex.org/sources?search={requests.utils.quote(journal_name)}&per_page=1"

        resp = requests.get(url, timeout=15)
        data = resp.json()
        results = data.get('results', [])
        if not results:
            return None

        source = results[0]
        if not _openalex_source_matches(source, journal_name, issn):
            return None

        stats = source.get('summary_stats', {})

        return {
            'openalex_id': source.get('id', ''),
            'h_index': stats.get('h_index'),
            'i10_index': stats.get('i10_index'),
            '2yr_mean_citedness': round(stats.get('2yr_mean_citedness', 0), 2),
            'cited_by_count': source.get('cited_by_count'),
            'works_count': source.get('works_count'),
            'oa_works_count': source.get('oa_works_count'),
            'is_oa': source.get('is_oa'),
            'is_in_doaj': source.get('is_in_doaj'),
            'host_organization': source.get('host_organization_name', ''),
            'country': source.get('country_code', ''),
            'apc_usd': _extract_apc_usd(source.get('apc_prices', [])),
        }
    except Exception as e:
        print(f"OpenAlex 查询失败 [{journal_name}]: {e}")
        return None


def _extract_apc_usd(apc_prices: list) -> Optional[int]:
    """从 apc_prices 提取 USD 价格"""
    for p in apc_prices:
        if p.get('currency') == 'USD':
            return p.get('price')
    return apc_prices[0].get('price') if apc_prices else None


def _openalex_source_matches(source: Dict, journal_name: str, issn: str = None) -> bool:
    """Return True when an OpenAlex source plausibly matches the requested journal."""
    if issn:
        target_issn = _normalize_issn(issn)
        source_issns = [
            _normalize_issn(value)
            for value in [source.get('issn_l'), *_as_list(source.get('issn'))]
            if value
        ]
        if target_issn and target_issn in source_issns:
            return True

    target_name = _normalize_source_name(journal_name)
    source_names = [
        _normalize_source_name(value)
        for value in [source.get('display_name'), *_as_list(source.get('alternate_titles'))]
        if value
    ]
    return bool(target_name and any(target_name == name for name in source_names))


def _as_list(value) -> List:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_issn(value: str) -> str:
    return re.sub(r'[^0-9Xx]', '', str(value or '')).upper()


def _normalize_source_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def get_journal_metrics(journal_name: str, use_cache: bool = True) -> Dict:
    """
    聚合多源期刊公开指标

    Returns:
        {
            'name': 期刊名,
            'shortname': 简称,
            'issn': ISSN,
            # 来自 LetPub
            'impact_factor': 影响因子,
            'partition': 中科院分区（如 '1区'）,
            'partition_detail': {'大类': ..., '小类': ..., 'Top': ...},
            'sci_type': SCIE/ESCI/无,
            'speed': 审稿速度,
            'accept': 录用比例,
            'warning': 是否预警,
            'publisher_letpub': 出版商(LetPub),
            'field': 研究方向,
            # 来自 OpenAlex
            'h_index': h指数,
            '2yr_mean_citedness': 2年平均被引（类IF）,
            'cited_by_count': 总被引,
            'works_count': 总论文数,
            'is_oa': 是否OA,
            'apc_usd': 文章处理费(USD),
            'publisher_oa': 出版商(OpenAlex),
            # 来源标记
            '_sources': ['letpub', 'openalex'],
        }
    """
    cache = _load_cache()

    # 检查缓存
    if use_cache and journal_name in cache:
        cached = cache[journal_name]
        cached_sources = set(cached.get('_sources', []))
        is_complete = {'letpub', 'openalex'}.issubset(cached_sources) and not cached.get('_source_errors')
        if is_complete and time.time() - cached.get('_cached_at', 0) < CACHE_TTL:
            return cached

    result = {'name': journal_name, '_sources': [], '_source_errors': {}, '_cached_at': time.time()}

    # 1. LetPub
    letpub = _get_letpub_info(journal_name)
    if letpub:
        result.update({
            'shortname': letpub.get('shortname', ''),
            'issn': letpub.get('issn', ''),
            'impact_factor': letpub.get('impact_factor'),
            'partition': _extract_partition(letpub),
            'partition_detail': letpub.get('ch_sci_2025'),
            'sci_type': letpub.get('_sci_type', ''),
            'speed': letpub.get('speed', ''),
            'accept': letpub.get('accept', ''),
            'warning': letpub.get('warning', False),
            'publisher_letpub': letpub.get('publisher', ''),
            'field': letpub.get('field', ''),
        })
        result['_sources'].append('letpub')
        time.sleep(1)  # LetPub 请求间隔
    else:
        result['_source_errors']['letpub'] = 'not found or request failed'

    # 2. OpenAlex（用 ISSN 或名称）
    issn = result.get('issn', '')
    openalex = _get_openalex_info(journal_name, issn if issn else None)
    if openalex:
        result.update({
            'h_index': openalex.get('h_index'),
            '2yr_mean_citedness': openalex.get('2yr_mean_citedness'),
            'cited_by_count': openalex.get('cited_by_count'),
            'works_count': openalex.get('works_count'),
            'oa_works_count': openalex.get('oa_works_count'),
            'is_oa': openalex.get('is_oa'),
            'is_in_doaj': openalex.get('is_in_doaj'),
            'apc_usd': openalex.get('apc_usd'),
            'publisher_oa': openalex.get('host_organization', ''),
        })
        result['_sources'].append('openalex')
    else:
        result['_source_errors']['openalex'] = 'not found or request failed'

    # 只缓存完整结果，避免一次临时网络失败污染后续推荐。
    if result['_sources'] and not result['_source_errors']:
        cache[journal_name] = result
        _save_cache(cache)

    return result


def _extract_partition(letpub_detail: Dict) -> str:
    """从 LetPub 详情提取分区文本"""
    if letpub_detail.get('partition'):
        return letpub_detail.get('partition', '')
    p = letpub_detail.get('ch_sci_2025')
    if isinstance(p, dict):
        return p.get('分区', '')
    elif isinstance(p, str):
        return p
    # fallback: sci_part
    return letpub_detail.get('sci_part', '')


def batch_metrics(journal_names: List[str], delay: float = 1.0) -> Dict[str, Dict]:
    """批量获取期刊指标"""
    results = {}
    unique_names = list(set(journal_names))
    for i, name in enumerate(unique_names):
        metrics = get_journal_metrics(name)
        if metrics.get('_sources'):
            results[name] = metrics
        if i < len(unique_names) - 1:
            time.sleep(delay)
    return results


def format_metrics_line(m: Dict) -> str:
    """一行格式化期刊指标"""
    parts = []

    # 收录类型
    sci = m.get('sci_type', '')
    if sci:
        s = sci.upper().replace(' ', '')
        if 'SCIE' in s:
            parts.append('SCIE')
        elif 'ESCI' in s:
            parts.append('⚠️ESCI')
        elif 'SSCI' in s:
            parts.append('SSCI')
        elif s != '无':
            parts.append(sci)
        else:
            parts.append('❌非SCI')
    elif 'letpub' in m.get('_sources', []):
        parts.append('❌非SCI')

    # IF
    if m.get('impact_factor'):
        parts.append(f"IF={m['impact_factor']}")

    # 分区
    p = m.get('partition', '')
    if p:
        parts.append(f"中科院{p}")

    # SJR Q分区（如果有的话）
    # h-index
    if m.get('h_index'):
        parts.append(f"h={m['h_index']}")

    # 审稿速度
    if m.get('speed'):
        speed = m['speed'].split('；')[0].replace('网友分享经验：', '').strip()
        if speed and len(speed) < 30:
            parts.append(speed)

    # OA
    if m.get('is_oa') is not None:
        oa_str = 'OA'
        if m.get('apc_usd'):
            oa_str += f"(${m['apc_usd']})"
        parts.append(oa_str if m['is_oa'] else '非OA')

    # 预警
    if m.get('warning'):
        parts.append('⚠️预警')

    return ' | '.join(parts) if parts else '无信息'


if __name__ == '__main__':
    for name in ['Journal of Hydrology', 'Water Resources Research', 'Water']:
        m = get_journal_metrics(name)
        print(f"{name}: {format_metrics_line(m)}")
