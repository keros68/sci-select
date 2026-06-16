#!/usr/bin/env python3
"""
sci-aiselect 完整测试脚本

测试 Journal Finder 和 AI 匹配功能
"""
import sys
import os

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from journal_finders import search_all_journal_finders


def test_paper(title, abstract, keywords=None):
    """测试指定论文的期刊匹配"""
    print("=" * 70)
    print(f"标题: {title[:80]}...")
    print("=" * 70)

    config = {
        'timeout': 90000,
        'retry_count': 1,
        'elsevier': {'enabled': True},
        'wiley': {'enabled': True},
        'taylor_francis': {'enabled': True},
        'springer': {'enabled': True},
        'wos': {'enabled': True},
    }

    results = search_all_journal_finders(title, abstract, keywords or [], config)

    print(f"\n共找到 {len(results)} 个期刊")

    by_source = {}
    for r in results:
        source = r['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(r)

    for source, journals in by_source.items():
        print(f"\n{source}: {len(journals)} 个期刊")
        for j in journals[:5]:
            print(f"  - {j['journal_name']} (匹配度: {j['match_score']:.2f})")

    return results


if __name__ == "__main__":
    # 使用示例：替换为实际论文标题和摘要
    title = "Your paper title here"
    abstract = "Your paper abstract here..."
    keywords = ["keyword1", "keyword2"]

    test_paper(title, abstract, keywords)
