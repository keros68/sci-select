"""
Journal Finder 测试脚本

测试 Journal Finder 模块的功能
"""
import sys
import os

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from journal_finders import (
    JournalFinderManager,
    search_all_journal_finders,
    JournalFinderResult
)


def test_journal_finder_manager():
    """测试 Journal Finder 管理器"""
    print("=" * 60)
    print("测试 Journal Finder 管理器")
    print("=" * 60)
    
    # 创建管理器
    manager = JournalFinderManager()
    
    # 列出可用的 Journal Finder
    finders = manager.list_finders()
    print(f"\n可用的 Journal Finder: {finders}")
    
    # 测试搜索
    title = "Groundwater nitrate source identification using stable isotopes"
    abstract = "This study investigates the sources of nitrate contamination in groundwater using stable isotopes of nitrogen and oxygen. The research was conducted in an agricultural watershed with intensive farming activities."
    keywords = ["groundwater", "nitrate", "stable isotopes", "hydrochemistry"]
    
    print(f"\n测试搜索:")
    print(f"标题: {title}")
    print(f"摘要: {abstract[:100]}...")
    print(f"关键词: {keywords}")
    
    # 执行搜索
    results = manager.search(title, abstract, keywords)
    
    print(f"\n搜索结果: {len(results)} 个期刊")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result.journal_name} (匹配度: {result.match_score:.2f})")
    
    return results


def test_individual_finders():
    """测试单个 Journal Finder"""
    print("\n" + "=" * 60)
    print("测试单个 Journal Finder")
    print("=" * 60)
    
    title = "Machine learning for crop yield prediction"
    abstract = "This paper presents a machine learning approach for predicting crop yields using satellite imagery and weather data."
    keywords = ["machine learning", "crop yield", "prediction", "remote sensing"]
    
    # 测试每个 Journal Finder
    from journal_finders import (
        ElsevierJournalFinder,
        WileyJournalFinder,
        TaylorFrancisJournalFinder,
        SpringerJournalFinder,
        WosJournalFinder
    )
    
    finders = [
        ("Elsevier", ElsevierJournalFinder),
        ("Wiley", WileyJournalFinder),
        ("Taylor & Francis", TaylorFrancisJournalFinder),
        ("Springer", SpringerJournalFinder),
        ("WOS", WosJournalFinder),
    ]
    
    for name, finder_class in finders:
        print(f"\n测试 {name}:")
        try:
            finder = finder_class()
            results = finder.search_with_retry(title, abstract, keywords)
            print(f"  结果: {len(results)} 个期刊")
            for result in results[:3]:
                print(f"  - {result.journal_name} ({result.match_score:.2f})")
        except Exception as e:
            print(f"  错误: {e}")


def test_convenience_functions():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("测试便捷函数")
    print("=" * 60)
    
    title = "Deep learning for medical image segmentation"
    abstract = "We propose a deep learning architecture for medical image segmentation that achieves state-of-the-art performance on multiple benchmarks."
    keywords = ["deep learning", "medical imaging", "segmentation"]
    
    print(f"\n测试 search_all_journal_finders:")
    results = search_all_journal_finders(title, abstract, keywords)
    
    print(f"结果: {len(results)} 个期刊")
    for result in results[:5]:
        print(f"- {result['journal_name']} (来源: {result['source']}, 匹配度: {result['match_score']:.2f})")


def main():
    """主函数"""
    print("sci-aiselect Journal Finder 测试")
    print("=" * 60)
    
    # 测试管理器
    test_journal_finder_manager()
    
    # 测试单个 Journal Finder
    test_individual_finders()
    
    # 测试便捷函数
    test_convenience_functions()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
