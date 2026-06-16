"""
Wiley Journal Finder 客户端

使用 Playwright 自动处理 cookie 弹窗并搜索期刊
需要分别输入标题和摘要
"""
from __future__ import annotations

import re
import json
import asyncio
from typing import Dict, List, Optional

from .base import BaseJournalFinder, JournalFinderResult


class WileyJournalFinder(BaseJournalFinder):
    """Wiley Journal Finder 客户端"""
    
    SOURCE_NAME = "wiley"
    BASE_URL = "https://www.wiley.com/en-ie/journal-finder/abstract/?type=match"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 90000)
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """搜索 Wiley 期刊 - 需要分别输入标题和摘要"""
        if not title and not abstract:
            return []
        
        try:
            results = asyncio.run(self._search_async(title, abstract, keywords))
            return self._filter_results(results)
        
        except Exception as e:
            print(f"[Wiley] 搜索失败: {e}")
            return []
    
    async def _search_async(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """异步搜索"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[Wiley] 需要安装 playwright")
            return []
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            
            page = await context.new_page()
            
            try:
                print(f"[Wiley] 访问 {self.BASE_URL}...")
                await page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(8000)
                
                # 处理 cookie 同意弹窗
                await self._handle_cookie_consent(page)
                
                # 填写标题框
                print("[Wiley] 填写标题...")
                title_input = await page.wait_for_selector(
                    'textarea[name="term"]',
                    timeout=10000
                )
                if title_input:
                    await title_input.fill(title[:2000])
                    await title_input.dispatch_event('input')
                
                # 填写摘要框
                print("[Wiley] 填写摘要...")
                abstract_input = await page.wait_for_selector(
                    'textarea[name="abstract"]',
                    timeout=10000
                )
                if abstract_input:
                    abstract_text = abstract if abstract else " ".join(keywords or [])
                    await abstract_input.fill(abstract_text[:3000])
                    await abstract_input.dispatch_event('input')
                
                # 等待按钮变为可用
                print("[Wiley] 等待搜索按钮变为可用...")
                await page.wait_for_timeout(3000)
                
                # 查找并点击搜索按钮
                submit_button = await page.query_selector(
                    'button:has-text("FIND JOURNALS")'
                )
                
                if submit_button:
                    # 等待按钮启用
                    for _ in range(15):
                        if await submit_button.is_enabled():
                            break
                        await page.wait_for_timeout(1000)
                    
                    if await submit_button.is_enabled():
                        print("[Wiley] 点击搜索按钮...")
                        await submit_button.click()
                        
                        # 等待结果加载
                        print("[Wiley] 等待结果...")
                        await page.wait_for_timeout(15000)
                        
                        # 提取结果
                        results = await self._extract_results(page)
                        print(f"[Wiley] 找到 {len(results)} 个期刊")
                    else:
                        print("[Wiley] 按钮仍未启用")
                
            except Exception as e:
                print(f"[Wiley] 浏览器操作失败: {e}")
            
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
                        print(f"[Wiley] 已点击 cookie 同意按钮")
                        await page.wait_for_timeout(1000)
                        return
                except:
                    continue
        
        except Exception as e:
            pass
    
    async def _extract_results(self, page) -> List[JournalFinderResult]:
        """
        提取搜索结果
        
        Wiley 结果格式：
        OFFERS OPEN ACCESS
        Journal Name
        30 days
        Submission to first decision
        ...
        """
        results = []
        
        try:
            # 获取页面全部文本
            text = await page.inner_text('body')
            
            # 查找 "Showing X journals" 之后的内容
            showing_idx = text.find('Showing')
            if showing_idx != -1:
                text = text[showing_idx:]
            
            # 按行分割
            lines = text.split('\n')
            seen_names = set()
            rank = 0
            
            # 标记是否在结果区域
            in_results = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if not line or len(line) < 3:
                    continue
                
                # 检测是否进入结果区域
                if 'showing' in line.lower() and 'journals' in line.lower():
                    in_results = True
                    continue
                
                if not in_results:
                    continue
                
                # 检测是否离开结果区域
                if 'prev' in line.lower() and i > 10:
                    break
                if 'publish my work' in line.lower() and i > 20:
                    break
                
                # 跳过无关文本
                skip_words = ['offering open access', 'fully open access', 'days',
                             'submission to first decision', 'acceptance rate',
                             'article publication charge', 'journal impact factor',
                             'relevance', 'compare', 'sort by', 'subject areas',
                             'topics', 'access options', 'showing', 'results',
                             'prev', 'next', 'of']
                if any(word in line.lower() for word in skip_words):
                    continue
                
                # 检查是否是期刊名称
                # 期刊名称特征：首字母大写，长度适中，不是数字或百分比
                if (line[0].isupper() and 
                    10 < len(line) < 150 and 
                    not line.replace('.', '').replace('%', '').isdigit() and
                    'days' not in line.lower()):
                    
                    if line.lower() not in seen_names:
                        seen_names.add(line.lower())
                        rank += 1
                        match_score = max(0.1, 1.0 - (rank - 1) * 0.05)
                        
                        result = JournalFinderResult(
                            journal_name=line,
                            match_score=match_score,
                            publisher='Wiley',
                            source=self.SOURCE_NAME,
                            raw_data={'rank': rank},
                        )
                        results.append(result)
                        
                        # 最多提取 10 个
                        if rank >= 10:
                            break
        
        except Exception as e:
            print(f"[Wiley] 提取结果失败: {e}")
        
        return results


def search_wiley_journals(title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
    """搜索 Wiley 期刊"""
    finder = WileyJournalFinder()
    results = finder.search_with_retry(title, abstract, keywords)
    return [r.to_dict() for r in results]
