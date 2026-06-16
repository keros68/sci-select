"""
Taylor & Francis Journal Suggester 客户端

使用 Playwright 自动处理 cookie 弹窗并搜索期刊
两列卡片布局，需要提取前 10 个结果
"""
from __future__ import annotations

import re
import json
import asyncio
from typing import Dict, List, Optional

from .base import BaseJournalFinder, JournalFinderResult


class TaylorFrancisJournalFinder(BaseJournalFinder):
    """Taylor & Francis Journal Suggester 客户端"""
    
    SOURCE_NAME = "taylor_francis"
    BASE_URL = "https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 90000)
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """搜索 Taylor & Francis 期刊"""
        if not title and not abstract:
            return []
        
        try:
            results = asyncio.run(self._search_async(title, abstract, keywords))
            return self._filter_results(results)
        
        except Exception as e:
            print(f"[Taylor & Francis] 搜索失败: {e}")
            return []
    
    async def _search_async(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """异步搜索"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[Taylor & Francis] 需要安装 playwright")
            return []
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print(f"[Taylor & Francis] 访问 {self.BASE_URL}...")
                await page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(5000)
                
                # 处理 cookie 同意弹窗
                await self._handle_cookie_consent(page)
                
                # 构建搜索文本 - 优先使用摘要
                search_text = abstract if abstract else title
                if keywords:
                    search_text += " " + " ".join(keywords)
                
                # 查找并填写搜索框
                print("[Taylor & Francis] 填写搜索文本...")
                search_input = await page.wait_for_selector(
                    'textarea[placeholder*="abstract"], input[placeholder*="abstract"]',
                    timeout=10000
                )
                
                if search_input:
                    await search_input.fill(search_text[:5000])
                    await page.wait_for_timeout(1000)
                    await search_input.dispatch_event('input')
                    await page.wait_for_timeout(1000)
                    
                    # 查找并点击搜索按钮
                    print("[Taylor & Francis] 点击搜索按钮...")
                    submit_button = await page.query_selector(
                        'button:has-text("Reveal suggested journals")'
                    )
                    
                    if submit_button:
                        await submit_button.click()
                        
                        # 等待结果加载
                        print("[Taylor & Francis] 等待结果...")
                        await page.wait_for_timeout(15000)
                        
                        # 提取结果
                        results = await self._extract_results(page)
                        print(f"[Taylor & Francis] 找到 {len(results)} 个期刊")
                
            except Exception as e:
                print(f"[Taylor & Francis] 浏览器操作失败: {e}")
            
            finally:
                await browser.close()
        
        return results
    
    async def _handle_cookie_consent(self, page):
        """处理 cookie 同意弹窗"""
        try:
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept all")',
                'button:has-text("Accept cookies")',
                '#onetrust-accept-btn-handler',
            ]
            
            for selector in consent_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        print(f"[Taylor & Francis] 已点击 cookie 同意按钮")
                        await page.wait_for_timeout(1000)
                        return
                except:
                    continue
        
        except Exception as e:
            pass
    
    async def _extract_results(self, page) -> List[JournalFinderResult]:
        """
        提取搜索结果（使用排名作为匹配度）
        
        Taylor & Francis 是两列卡片布局，每个卡片包含：
        - 期刊名称
        - "AboutMetrics" 文本
        - 期刊描述
        - "Learn more" 链接
        """
        results = []
        
        try:
            # 获取页面全部文本
            text = await page.inner_text('body')
            
            # 查找 "Suggested Journals" 之后的内容
            start_idx = text.find('Suggested Journals')
            if start_idx == -1:
                start_idx = text.find('Suggested journals')
            
            if start_idx != -1:
                text = text[start_idx:]
            
            # 按行分割
            lines = text.split('\n')
            seen_names = set()
            rank = 0
            
            # 标记是否在建议期刊区域
            in_suggested_section = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if not line or len(line) < 3:
                    continue
                
                # 检测是否进入建议期刊区域
                if 'suggested journals' in line.lower():
                    in_suggested_section = True
                    continue
                
                if not in_suggested_section:
                    continue
                
                # 检测是否离开建议期刊区域
                if 'improve the journal suggester' in line.lower():
                    break
                if 'contact us' in line.lower() and i > 10:
                    break
                if 'cookie policy' in line.lower():
                    break
                
                # 跳过无关文本
                skip_words = ['definitions:', 'an open access journal', 'open select:',
                             'choose to publish open access', 'aboutmetrics',
                             'publishes', 'research on', 'including', 'and their',
                             'learn more', 'or visit', 'cost finder', 'calculate',
                             'article publishing charge', 'improve', 'suggester',
                             'artificial intelligence', 'help us', 'answering',
                             'short questions', 'contact us', 'cookie policy',
                             'accessibility', 'privacy', 'terms', 'editorial',
                             'taylor', 'francis', 'online', 'f1000', 'editing',
                             'services', 'editor', 'resources', 'books', 'authors',
                             'ebooks', 'informa', 'limited', 'group', 'company',
                             'registered', 'office', 'howick', 'place', 'london',
                             'england', 'wales', 'number', 'vat']
                if any(word in line.lower() for word in skip_words):
                    continue
                
                # 检查是否是期刊名称
                # 期刊名称特征：
                # 1. 首字母大写
                # 2. 长度在 10-150 字符之间
                # 3. 不以常见非期刊词开头
                if line[0].isupper() and 10 < len(line) < 150:
                    # 排除明显不是期刊的行
                    exclude_starts = ['The ',                        'This ', 'Formerly ', 'Promotes ', 'Addresses ']
                    if any(line.startswith(excl) for excl in exclude_starts):
                        continue
                    
                    if line.lower() not in seen_names:
                        seen_names.add(line.lower())
                        rank += 1
                        match_score = max(0.1, 1.0 - (rank - 1) * 0.05)
                        
                        result = JournalFinderResult(
                            journal_name=line,
                            match_score=match_score,
                            publisher='Taylor & Francis',
                            source=self.SOURCE_NAME,
                            raw_data={'rank': rank},
                        )
                        results.append(result)
                        
                        # 最多提取 10 个
                        if rank >= 10:
                            break
        
        except Exception as e:
            print(f"[Taylor & Francis] 提取结果失败: {e}")
        
        return results


def search_taylor_francis_journals(title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
    """搜索 Taylor & Francis 期刊"""
    finder = TaylorFrancisJournalFinder()
    results = finder.search_with_retry(title, abstract, keywords)
    return [r.to_dict() for r in results]
