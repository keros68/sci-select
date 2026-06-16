"""
Elsevier Journal Finder 客户端

使用 Playwright 自动处理 cookie 弹窗并搜索期刊
匹配度通过排名计算（排名越前匹配度越高）
"""
from __future__ import annotations

import re
import json
import asyncio
from typing import Dict, List, Optional

from .base import BaseJournalFinder, JournalFinderResult


class ElsevierJournalFinder(BaseJournalFinder):
    """Elsevier Journal Finder 客户端"""
    
    SOURCE_NAME = "elsevier"
    BASE_URL = "https://journalfinder.elsevier.com/"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 90000)
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """搜索 Elsevier 期刊"""
        search_text = self._prepare_search_text(title, abstract, keywords)
        
        if not search_text:
            return []
        
        try:
            results = asyncio.run(self._search_async(search_text))
            return self._filter_results(results)
        
        except Exception as e:
            print(f"[Elsevier] 搜索失败: {e}")
            return []
    
    async def _search_async(self, search_text: str) -> List[JournalFinderResult]:
        """异步搜索"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[Elsevier] 需要安装 playwright")
            return []
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print(f"[Elsevier] 访问 {self.BASE_URL}...")
                await page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 处理 cookie 同意弹窗
                await self._handle_cookie_consent(page)
                
                # 查找并填写搜索框
                print("[Elsevier] 填写搜索文本...")
                search_input = await page.wait_for_selector(
                    'textarea, input[type="text"]',
                    timeout=10000
                )
                
                if search_input:
                    await search_input.fill(search_text[:5000])
                    
                    # 查找并点击搜索按钮
                    print("[Elsevier] 点击搜索按钮...")
                    submit_button = await page.query_selector(
                        'button[type="submit"], button:has-text("Find journals")'
                    )
                    
                    if submit_button:
                        await submit_button.click()
                        
                        # 等待结果加载
                        print("[Elsevier] 等待结果...")
                        await page.wait_for_timeout(10000)
                        
                        # 提取结果
                        results = await self._extract_results(page)
                        print(f"[Elsevier] 找到 {len(results)} 个期刊")
                
            except Exception as e:
                print(f"[Elsevier] 浏览器操作失败: {e}")
            
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
                        print(f"[Elsevier] 已点击 cookie 同意按钮")
                        await page.wait_for_timeout(1000)
                        return
                except:
                    continue
        
        except Exception as e:
            pass
    
    async def _extract_results(self, page) -> List[JournalFinderResult]:
        """提取搜索结果（使用排名作为匹配度）"""
        results = []
        
        try:
            # 获取页面全部文本
            text = await page.inner_text('body')
            
            # 按行分割，查找 'Save journal' 前面的行
            lines = text.split('\n')
            seen_names = set()
            rank = 0
            
            for i, line in enumerate(lines):
                if line.strip() == 'Save journal' and i > 0:
                    name = lines[i-1].strip()
                    
                    # 过滤无效名称
                    if not name or len(name) < 3:
                        continue
                    
                    # 去重
                    if name.lower() in seen_names:
                        continue
                    
                    seen_names.add(name.lower())
                    rank += 1
                    
                    # 计算匹配度（基于排名）
                    match_score = max(0.1, 1.0 - (rank - 1) * 0.05)
                    
                    result = JournalFinderResult(
                        journal_name=name,
                        match_score=match_score,
                        publisher='Elsevier',
                        source=self.SOURCE_NAME,
                        raw_data={'rank': rank},
                    )
                    results.append(result)
        
        except Exception as e:
            print(f"[Elsevier] 提取结果失败: {e}")
        
        return results


def search_elsevier_journals(title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
    """搜索 Elsevier 期刊"""
    finder = ElsevierJournalFinder()
    results = finder.search_with_retry(title, abstract, keywords)
    return [r.to_dict() for r in results]
