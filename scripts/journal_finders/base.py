"""
Journal Finder 基类

提供统一的接口和通用功能
"""
from __future__ import annotations

import re
import time
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class JournalFinderResult:
    """Journal Finder 结果数据类"""
    journal_name: str
    match_score: float  # 0-1
    issn: str = ""
    publisher: str = ""
    url: str = ""
    source: str = ""  # 来源，如 "elsevier", "wiley"
    raw_data: Dict = None  # 原始数据，用于调试
    fetched_at: str = ""  # 获取时间
    
    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now().isoformat()
        if self.raw_data is None:
            self.raw_data = {}
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JournalFinderResult':
        """从字典创建"""
        return cls(**data)


class BaseJournalFinder(ABC):
    """Journal Finder 基类"""
    
    # 子类需要覆盖的属性
    SOURCE_NAME: str = ""  # 来源名称，如 "elsevier"
    BASE_URL: str = ""  # 基础 URL
    TIMEOUT: int = 30  # 超时时间（秒）
    RETRY_COUNT: int = 3  # 重试次数
    
    def __init__(self, config: Dict = None):
        """
        初始化
        
        Args:
            config: 配置字典，可能包含：
                - timeout: 超时时间
                - retry_count: 重试次数
                - proxy: 代理配置
                - cookies: cookies
                - api_key: API key
        """
        self.config = config or {}
        self.timeout = self.config.get('timeout', self.TIMEOUT)
        self.retry_count = self.config.get('retry_count', self.RETRY_COUNT)
    
    @abstractmethod
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """
        搜索期刊
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            keywords: 关键词列表（可选）
        
        Returns:
            List[JournalFinderResult]: 期刊结果列表
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError
    
    def search_with_retry(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """
        带重试的搜索
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            keywords: 关键词列表
        
        Returns:
            List[JournalFinderResult]: 期刊结果列表
        """
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                results = self.search(title, abstract, keywords)
                return results
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        
        # 所有重试都失败
        print(f"[{self.SOURCE_NAME}] 搜索失败: {last_error}")
        return []
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        if not text:
            return ""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def _extract_issn(self, text: str) -> str:
        """从文本中提取 ISSN"""
        if not text:
            return ""
        
        # ISSN 格式: XXXX-XXXX
        match = re.search(r'\b(\d{4}-\d{4})\b', text)
        if match:
            return match.group(1)
        
        return ""
    
    def _calculate_match_score(self, raw_score: float, max_score: float = 100) -> float:
        """
        计算归一化的匹配分数
        
        Args:
            raw_score: 原始分数
            max_score: 最大分数
        
        Returns:
            float: 归一化的分数 (0-1)
        """
        if max_score <= 0:
            return 0.0
        
        normalized = min(1.0, max(0.0, raw_score / max_score))
        return round(normalized, 4)
    
    def _merge_keywords(self, keywords: List[str], separator: str = " ") -> str:
        """合并关键词"""
        if not keywords:
            return ""
        return separator.join(keywords)
    
    def _prepare_search_text(self, title: str, abstract: str, keywords: List[str] = None) -> str:
        """
        准备搜索文本
        
        Args:
            title: 标题
            abstract: 摘要
            keywords: 关键词
        
        Returns:
            str: 合并后的搜索文本
        """
        parts = []
        
        if title:
            parts.append(self._normalize_text(title))
        
        if abstract:
            parts.append(self._normalize_text(abstract))
        
        if keywords:
            parts.append(self._merge_keywords(keywords))
        
        return " ".join(parts)
    
    def _validate_result(self, result: JournalFinderResult) -> bool:
        """验证结果是否有效"""
        if not result.journal_name:
            return False
        
        if not (0 <= result.match_score <= 1):
            return False
        
        return True
    
    def _filter_results(self, results: List[JournalFinderResult], max_results: int = 10) -> List[JournalFinderResult]:
        """
        过滤和排序结果
        
        Args:
            results: 原始结果列表
            max_results: 最大结果数
        
        Returns:
            List[JournalFinderResult]: 过滤后的结果
        """
        # 验证结果
        valid_results = [r for r in results if self._validate_result(r)]
        
        # 按匹配分数降序排序
        valid_results.sort(key=lambda r: r.match_score, reverse=True)
        
        # 限制结果数量
        return valid_results[:max_results]
    
    def _save_debug_data(self, data: Any, filename: str):
        """保存调试数据"""
        debug_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        
        filepath = os.path.join(debug_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def __repr__(self):
        return f"<{self.__class__.__name__} source={self.SOURCE_NAME}>"
