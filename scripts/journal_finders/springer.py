"""
Springer Journal Finder 客户端

使用 Playwright 自动处理 cookie 弹窗并搜索期刊
"""
from __future__ import annotations

import re
import json
import asyncio
from typing import Dict, List, Optional

from .base import BaseJournalFinder, JournalFinderResult


class SpringerJournalFinder(BaseJournalFinder):
    """Springer Journal Finder 客户端"""
    
    SOURCE_NAME = "springer"
    BASE_URL = "https://link.springer.com/journals"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 90000)
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """搜索 Springer 期刊"""
        if not title and not abstract:
            return []
        
        try:
            results = asyncio.run(self._search_async(title, abstract, keywords))
            return self._filter_results(results)
        
        except Exception as e:
            print(f"[Springer] 搜索失败: {e}")
            return []
    
    async def _search_async(self, title: str, abstract: str, keywords: List[str] = None) -> List[JournalFinderResult]:
        """异步搜索"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[Springer] 需要安装 playwright")
            return []
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print(f"[Springer] 访问 {self.BASE_URL}...")
                await page.goto(self.BASE_URL, wait_until='networkidle', timeout=self.timeout)
                await page.wait_for_timeout(5000)
                
                # 处理 cookie 同意弹窗
                await self._handle_cookie_consent(page)
                
                # 构建搜索文本
                search_text = title
                if abstract:
                    search_text += " " + abstract[:200]
                
                # 查找并填写搜索框
                print("[Springer] 填写搜索文本...")
                search_input = await page.wait_for_selector(
                    '#manuscript-abstract',
                    timeout=10000
                )
                
                if search_input:
                    await search_input.fill(search_text[:5000])
                    
                    # 查找并点击搜索按钮
                    print("[Springer] 点击搜索按钮...")
                    submit_button = await page.query_selector(
                        'button:has-text("Find journals")'
                    )
                    
                    if submit_button:
                        await submit_button.click()
                        
                        # 等待结果加载
                        print("[Springer] 等待结果...")
                        await page.wait_for_timeout(15000)
                        
                        # 提取结果
                        results = await self._extract_results(page)
                        print(f"[Springer] 找到 {len(results)} 个期刊")
                
            except Exception as e:
                print(f"[Springer] 浏览器操作失败: {e}")
            
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
                        print(f"[Springer] 已点击 cookie 同意按钮")
                        await page.wait_for_timeout(1000)
                        return
                except:
                    continue
        
        except Exception as e:
            pass
    
    async def _extract_results(self, page) -> List[JournalFinderResult]:
        """
        提取搜索结果
        
        Springer 结果格式：
        Journal Name
        Publishing Model
        Hybrid/Open access
        Journal Impact Factor
        X.X (2024)
        ...
        """
        results = []
        
        try:
            # 获取页面全部文本
            text = await page.inner_text('body')
            
            # 查找 "Showing" 之后的内容
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
                if 'showing' in line.lower() and 'results' in line.lower():
                    in_results = True
                    continue
                
                if not in_results:
                    continue
                
                # 检测是否离开结果区域
                if 'footer navigation' in line.lower():
                    break
                if 'download results' in line.lower() and i > 10:
                    break
                
                # 跳过无关文本
                skip_words = ['publishing model', 'hybrid', 'open access',
                             'journal impact factor', 'downloads', 'submission to first decision',
                             'median', 'days', 'not available', 'save journal',
                             'for open access', 'publishing costs', 'funding options',
                             'select your institution', 'subscription publishing',
                             'also available', 'update results', 'download results',
                             'sort by', '5-year', 'high to low', 'shortest to longest',
                             'relevance', 'funding']
                if any(word in line.lower() for word in skip_words):
                    continue
                
                # 跳过学科分类（通常在期刊信息之后）
                subject_areas = ['environmental sciences', 'ecology', 'atmospheric science',
                               'physical geography', 'environmental management', 'earth sciences',
                               'humanities and social sciences', 'biology', 'chemistry',
                               'climate sciences', 'conservation biology', 'geography',
                               'plant science', 'soil science', 'ocean sciences',
                               'geotechnical', 'biogeosciences', 'geochemistry', 'geology',
                               'biodiversity', 'pollution', 'forestry', 'agriculture',
                               'sustainability', 'public health', 'economics',
                               'landscape ecology', 'environmental chemistry',
                               'environmental monitoring', 'environmental economics',
                               'photosynthesis', 'agricultural genetics']
                if line.lower() in subject_areas:
                    continue
                
                # 检查是否是期刊名称
                # 期刊名称特征：首字母大写，长度适中，不是数字
                if (line[0].isupper() and 
                    5 < len(line) < 100 and 
                    not line.replace('.', '').replace('(', '').replace(')', '').replace(',', '').isdigit()):
                    
                    # 检查下一行是否是 "Publishing Model" 或包含期刊信息
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip().lower()
                        if 'publishing model' in next_line or 'journal impact factor' in next_line:
                            if line.lower() not in seen_names:
                                seen_names.add(line.lower())
                                rank += 1
                                match_score = max(0.1, 1.0 - (rank - 1) * 0.05)
                                
                                result = JournalFinderResult(
                                    journal_name=line,
                                    match_score=match_score,
                                    publisher='Springer',
                                    source=self.SOURCE_NAME,
                                    raw_data={'rank': rank},
                                )
                                results.append(result)
                                
                                if rank >= 10:
                                    break
        
        except Exception as e:
            print(f"[Springer] 提取结果失败: {e}")
        
        return results


def search_springer_journals(title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
    """搜索 Springer 期刊"""
    finder = SpringerJournalFinder()
    results = finder.search_with_retry(title, abstract, keywords)
    return [r.to_dict() for r in results]
