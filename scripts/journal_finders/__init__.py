"""
Journal Finder 模块

提供多个出版社的 Journal Finder 功能
使用 Playwright 自动处理 cookie 弹窗
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BaseJournalFinder, JournalFinderResult
from .elsevier import ElsevierJournalFinder, search_elsevier_journals
from .wiley import WileyJournalFinder, search_wiley_journals
from .taylor_francis import TaylorFrancisJournalFinder, search_taylor_francis_journals
from .springer import SpringerJournalFinder, search_springer_journals
from .wos import WosJournalFinder, search_wos_journals


# 所有可用的 Journal Finder
AVAILABLE_FINDERS = {
    'elsevier': ElsevierJournalFinder,
    'wiley': WileyJournalFinder,
    'taylor_francis': TaylorFrancisJournalFinder,
    'springer': SpringerJournalFinder,
    'wos': WosJournalFinder,
}

# 默认配置
DEFAULT_CONFIG = {
    'enabled': True,
    'timeout': 60000,
    'retry_count': 1,
    'max_results_per_finder': 10,
    'parallel': False,  # 默认串行，因为 Playwright 并行可能有问题
    'max_workers': 1,
}


class JournalFinderManager:
    """Journal Finder 管理器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化管理器
        
        Args:
            config: 配置字典
        """
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.finders = {}
        self._init_finders()
    
    def _init_finders(self):
        """初始化 Journal Finder"""
        for name, finder_class in AVAILABLE_FINDERS.items():
            # 检查是否启用
            finder_config = self.config.get(name, {})
            if not finder_config.get('enabled', True):
                continue
            
            try:
                finder = finder_class(config={
                    'timeout': self.config.get('timeout', 60000),
                    'retry_count': self.config.get('retry_count', 1),
                    **finder_config
                })
                self.finders[name] = finder
            except Exception as e:
                print(f"[JournalFinderManager] 初始化 {name} 失败: {e}")
    
    def search(
        self,
        title: str,
        abstract: str,
        keywords: List[str] = None,
        finders: List[str] = None,
        max_results: int = 50
    ) -> List[JournalFinderResult]:
        """
        搜索期刊
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            keywords: 关键词列表
            finders: 要使用的 Journal Finder 名称列表（None 表示全部）
            max_results: 最大结果数
        
        Returns:
            List[JournalFinderResult]: 期刊结果列表
        """
        if not title and not abstract:
            return []
        
        # 确定要使用的 Journal Finder
        active_finders = self._get_active_finders(finders)
        
        if not active_finders:
            print("[JournalFinderManager] 没有可用的 Journal Finder")
            return []
        
        # 串行搜索（Playwright 并行可能有问题）
        all_results = self._search_sequential(
            title, abstract, keywords, active_finders
        )
        
        # 去重和排序
        unique_results = self._deduplicate_results(all_results)
        
        # 限制结果数量
        return unique_results[:max_results]
    
    def _get_active_finders(self, finders: List[str] = None) -> Dict[str, BaseJournalFinder]:
        """获取活跃的 Journal Finder"""
        if finders is None:
            return self.finders
        
        return {
            name: finder
            for name, finder in self.finders.items()
            if name in finders
        }
    
    def _search_sequential(
        self,
        title: str,
        abstract: str,
        keywords: List[str],
        finders: Dict[str, BaseJournalFinder]
    ) -> List[JournalFinderResult]:
        """串行搜索"""
        all_results = []
        
        for name, finder in finders.items():
            try:
                print(f"\n[{name}] 开始搜索...")
                results = finder.search_with_retry(title, abstract, keywords)
                all_results.extend(results)
                print(f"[{name}] 找到 {len(results)} 个期刊")
            except Exception as e:
                print(f"[{name}] 搜索异常: {e}")
        
        return all_results
    
    def _deduplicate_results(self, results: List[JournalFinderResult]) -> List[JournalFinderResult]:
        """去重结果"""
        seen = set()
        unique_results = []
        
        for result in results:
            # 使用期刊名称作为去重键
            key = result.journal_name.lower().strip()
            
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        # 按匹配分数降序排序
        unique_results.sort(key=lambda r: r.match_score, reverse=True)
        
        return unique_results
    
    def get_finder(self, name: str) -> Optional[BaseJournalFinder]:
        """获取指定的 Journal Finder"""
        return self.finders.get(name)
    
    def list_finders(self) -> List[str]:
        """列出所有可用的 Journal Finder"""
        return list(self.finders.keys())
    
    def update_finder_config(self, name: str, config: Dict):
        """更新 Journal Finder 配置"""
        if name in self.finders:
            self.finders[name].config.update(config)


def search_all_journal_finders(
    title: str,
    abstract: str,
    keywords: List[str] = None,
    config: Dict = None
) -> List[Dict]:
    """
    搜索所有 Journal Finder
    
    Args:
        title: 论文标题
        abstract: 论文摘要
        keywords: 关键词列表
        config: 配置字典
    
    Returns:
        List[Dict]: 期刊结果列表
    """
    manager = JournalFinderManager(config)
    results = manager.search(title, abstract, keywords)
    return [r.to_dict() for r in results]


__all__ = [
    'BaseJournalFinder',
    'JournalFinderResult',
    'JournalFinderManager',
    'ElsevierJournalFinder',
    'WileyJournalFinder',
    'TaylorFrancisJournalFinder',
    'SpringerJournalFinder',
    'WosJournalFinder',
    'search_all_journal_finders',
    'search_elsevier_journals',
    'search_wiley_journals',
    'search_taylor_francis_journals',
    'search_springer_journals',
    'search_wos_journals',
    'AVAILABLE_FINDERS',
]
