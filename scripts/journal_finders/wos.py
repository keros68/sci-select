"""
Web of Science Master Journal List 客户端

使用 Playwright 搜索期刊，无需登录
"""
from __future__ import annotations

import re
import json
import asyncio
from typing import Dict, List, Optional

from .base import BaseJournalFinder, JournalFinderResult


class WosJournalFinder(BaseJournalFinder):
    """Web of Science Master Journal List 客户端"""
    
    SOURCE_NAME = "wos"
    BASE_URL = "https://mjl.clarivate.com/home"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 90000)
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """搜索 Web of Science 期刊"""
        if not title and not abstract:
            return []
        
        try:
            results = asyncio.run(self._search_async(title, abstract, keywords))
            return self._filter_results(results)
        
        except Exception as e:
            print(f"[WOS] 搜索失败: {e}")
            return []
    
    async def _search_async(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """异步搜索"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[WOS] 需要安装 playwright")
            return []
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print(f"[WOS] 访问 {self.BASE_URL}...")
                await page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(5000)
                
                # 处理 cookie 弹窗 - 更彻底的移除
                await self._handle_cookie_consent(page)
                
                # 构建搜索文本 - 使用关键词
                search_text = " ".join(keywords) if keywords else title
                if not search_text:
                    search_text = abstract[:200]
                
                # 查找并填写搜索框
                print(f"[WOS] 搜索: {search_text[:50]}...")
                search_input = await page.wait_for_selector(
                    'input[placeholder*="Search Journal"]',
                    timeout=10000
                )
                
                if search_input:
                    await search_input.fill(search_text[:200])
                    await page.wait_for_timeout(1000)
                    
                    # 使用键盘 Enter 提交
                    await search_input.press('Enter')
                    
                    # 等待结果加载
                    print("[WOS] 等待结果...")
                    await page.wait_for_timeout(10000)
                    
                    # 提取结果
                    results = await self._extract_results(page)
                    print(f"[WOS] 找到 {len(results)} 个期刊")
                
            except Exception as e:
                print(f"[WOS] 浏览器操作失败: {e}")
            
            finally:
                await browser.close()
        
        return results
    
    async def _handle_cookie_consent(self, page):
        """处理 cookie 同意弹窗 - 彻底移除"""
        try:
            await page.evaluate('''() => {
                // 移除所有 OneTrust 相关元素
                const elements = document.querySelectorAll('[id*="onetrust"], [class*="onetrust"]');
                elements.forEach(el => el.remove());
                
                // 移除遮罩层
                const overlays = document.querySelectorAll('.ot-fade-in, .onetrust-pc-dark-filter');
                overlays.forEach(el => el.remove());
                
                // 移除整个 consent SDK
                const sdk = document.querySelector('#onetrust-consent-sdk');
                if (sdk) sdk.remove();
            }''')
            await page.wait_for_timeout(1000)
        except:
            pass
    
    async def _extract_results(self, page) -> List[JournalFinderResult]:
        """
        提取搜索结果
        
        WOS 结果格式：
        JOURNAL_NAME (全大写)
        Publisher: ...
        ISSN / eISSN: ...
        Web of Science Core Collection: ...
        """
        results = []
        
        try:
            # 获取页面全部文本
            text = await page.inner_text('body')
            
            # 查找 "Journals Relevant To" 之后的内容
            start_idx = text.find('Journals Relevant To')
            if start_idx == -1:
                start_idx = text.find('Journals relevant to')
            
            if start_idx != -1:
                text = text[start_idx:]
            
            # 按行分割
            lines = text.split('\n')
            seen_names = set()
            rank = 0
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # 检测是否离开结果区域
                if 'items per page' in line.lower():
                    break
                if 'editorial disclaimer' in line.lower():
                    break
                
                # 检查是否是期刊名称（全大写，且不是出版社地址）
                if (line.isupper() and 
                    10 < len(line) < 100 and 
                    not any(skip in line.lower() for skip in ['publisher', 'issn', 'street', 'avenue', 'road', 'building', 'floor', 'suite', 'box', 'university', 'press', 'ltd', 'inc', 'corp', 'pvt', 'gmbh', 'co ', 'sa ', 'bv', 'ab', 'asa'])):
                    
                    # 额外检查：下一行应该是 "Publisher:" 或包含出版社信息
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if 'publisher:' in next_line.lower() or 'issn' in lines[i + 2].lower() if i + 2 < len(lines) else False:
                            if line.lower() not in seen_names:
                                seen_names.add(line.lower())
                                rank += 1
                                match_score = max(0.1, 1.0 - (rank - 1) * 0.05)
                                
                                result = JournalFinderResult(
                                    journal_name=line.title(),  # 转换为标题格式
                                    match_score=match_score,
                                    publisher='Clarivate',
                                    source=self.SOURCE_NAME,
                                    raw_data={'rank': rank},
                                )
                                results.append(result)
                                
                                if rank >= 10:
                                    break
                
                i += 1
        
        except Exception as e:
            print(f"[WOS] 提取结果失败: {e}")
        
        return results


def search_wos_journals(title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
    """搜索 Web of Science 期刊"""
    finder = WosJournalFinder()
    results = finder.search_with_retry(title, abstract, keywords)
    return [r.to_dict() for r in results]
