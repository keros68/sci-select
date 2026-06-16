"""
期刊学习和摘要润色模块

功能：
1. 学习期刊的 aim and scope
2. 分析最近发表的文献
3. 给出摘要润色建议
"""
from __future__ import annotations

import re
import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright


class JournalLearner:
    """期刊学习器"""
    
    def __init__(self):
        self.timeout = 60000
    
    async def learn_journal(self, journal_name: str) -> Dict:
        """
        学习期刊信息
        
        Args:
            journal_name: 期刊名称
        
        Returns:
            Dict: 期刊信息
        """
        print(f"\n正在学习期刊: {journal_name}")
        
        # 1. 搜索期刊官网
        journal_url = await self._find_journal_website(journal_name)
        
        # 2. 获取 aim and scope
        aim_scope = await self._get_aim_scope(journal_url)
        
        # 3. 获取最近发表的文章
        recent_articles = await self._get_recent_articles(journal_url)
        
        # 4. 分析文章风格
        style_analysis = self._analyze_style(recent_articles)
        
        return {
            'name': journal_name,
            'url': journal_url,
            'aim_scope': aim_scope,
            'recent_articles': recent_articles,
            'style_analysis': style_analysis,
        }
    
    async def _find_journal_website(self, journal_name: str) -> str:
        """查找期刊官网"""
        # 使用 Google 搜索
        search_query = f"{journal_name} official website"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 访问 Google 搜索
                await page.goto(f'https://www.google.com/search?q={search_query}', 
                              wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 提取第一个结果的链接
                links = await page.query_selector_all('a[href*="http"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and ('springer' in href or 'elsevier' in href or 'wiley' in href or 
                                'nature' in href or 'agu' in href or 'copernicus' in href):
                        return href
                
                return ""
            
            except Exception as e:
                print(f"查找期刊官网失败: {e}")
                return ""
            
            finally:
                await browser.close()
    
    async def _get_aim_scope(self, journal_url: str) -> str:
        """获取期刊的 aim and scope"""
        if not journal_url:
            return ""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(journal_url, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 查找 aim and scope 相关内容
                text = await page.inner_text('body')
                
                # 尝试提取 aim and scope
                aim_scope = self._extract_aim_scope(text)
                
                return aim_scope
            
            except Exception as e:
                print(f"获取 aim and scope 失败: {e}")
                return ""
            
            finally:
                await browser.close()
    
    def _extract_aim_scope(self, text: str) -> str:
        """从页面文本中提取 aim and scope"""
        # 查找 aim and scope 相关段落
        patterns = [
            r'(?:aims?\s*(?:and|&)\s*scope|about\s+(?:this\s+)?journal|journal\s+description|mission)[:\s]*(.*?)(?:(?:key\s*words|topics|scope\s+notes|submit|publish|contact)|\n\n|\Z)',
            r'(?:we\s+publish|this\s+journal|the\s+journal\s+publishes)[:\s]*(.*?)(?:(?:key\s*words|topics|scope\s+notes|submit|publish|contact)|\n\n|\Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:2000]
        
        return ""
    
    async def _get_recent_articles(self, journal_url: str) -> List[Dict]:
        """获取最近发表的文章"""
        if not journal_url:
            return []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(journal_url, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 查找文章列表
                articles = await self._extract_articles(page)
                
                return articles[:5]  # 只返回前 5 篇
            
            except Exception as e:
                print(f"获取最近文章失败: {e}")
                return []
            
            finally:
                await browser.close()
    
    async def _extract_articles(self, page) -> List[Dict]:
        """从页面提取文章信息"""
        articles = []
        
        try:
            # 查找文章标题元素
            title_elements = await page.query_selector_all('h3 a, h2 a, [class*="title"] a, [class*="article"] a')
            
            for elem in title_elements[:10]:
                title = await elem.inner_text()
                href = await elem.get_attribute('href')
                
                if title and len(title) > 20:
                    articles.append({
                        'title': title.strip(),
                        'url': href or '',
                    })
        
        except Exception as e:
            print(f"提取文章失败: {e}")
        
        return articles
    
    def _analyze_style(self, articles: List[Dict]) -> Dict:
        """分析文章风格"""
        if not articles:
            return {
                'typical_length': 'unknown',
                'common_structure': 'unknown',
                'writing_style': 'unknown',
            }
        
        # 分析标题风格
        titles = [a['title'] for a in articles]
        
        # 标题长度统计
        avg_length = sum(len(t) for t in titles) / len(titles) if titles else 0
        
        # 常见词汇
        common_words = []
        for title in titles:
            words = title.lower().split()
            common_words.extend(words)
        
        # 统计词频
        word_freq = {}
        for word in common_words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 排序
        sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
        
        return {
            'typical_title_length': f"{avg_length:.0f} 字符",
            'common_title_words': [w for w, _ in sorted_words[:10]],
            'article_count': len(articles),
        }


def suggest_abstract_revision(
    original_abstract: str,
    journal_info: Dict,
    title: str = "",
) -> str:
    """
    根据期刊信息给出摘要润色建议
    
    Args:
        original_abstract: 原始摘要
        journal_info: 期刊信息
        title: 论文标题
    
    Returns:
        str: 润色建议
    """
    suggestions = []
    
    # 1. 长度建议
    word_count = len(original_abstract.split())
    if word_count < 150:
        suggestions.append("- 摘要偏短（当前约 {} 词），建议扩展到 150-250 词，增加研究方法和结果的详细描述".format(word_count))
    elif word_count > 300:
        suggestions.append("- 摘要偏长（当前约 {} 词），建议精简到 150-250 词，突出核心发现".format(word_count))
    else:
        suggestions.append("- 摘要长度合适（当前约 {} 词）".format(word_count))
    
    # 2. 结构建议
    has_background = any(w in original_abstract.lower() for w in ['background', 'introduction', 'context', 'motivation'])
    has_methods = any(w in original_abstract.lower() for w in ['method', 'approach', 'data', 'analysis', 'observation'])
    has_results = any(w in original_abstract.lower() for w in ['result', 'finding', 'show', 'reveal', 'indicate'])
    has_conclusion = any(w in original_abstract.lower() for w in ['conclusion', 'implication', 'suggest', 'highlight'])
    
    if not has_background:
        suggestions.append("- 建议在开头明确研究背景和动机")
    if not has_methods:
        suggestions.append("- 建议简要说明研究方法或数据来源")
    if not has_results:
        suggestions.append("- 建议突出核心研究结果")
    if not has_conclusion:
        suggestions.append("- 建议在结尾总结研究意义或启示")
    
    # 3. 期刊风格建议
    aim_scope = journal_info.get('aim_scope', '')
    if aim_scope:
        # 分析期刊关注的主题
        focus_areas = []
        keywords = ['climate', 'environment', 'ecology', 'hydrology', 'geology', 
                   'remote sensing', 'GIS', 'sustainability', 'hazard', 'risk']
        for keyword in keywords:
            if keyword in aim_scope.lower():
                focus_areas.append(keyword)
        
        if focus_areas:
            suggestions.append("- 该期刊关注以下主题：{}，建议在摘要中强调与这些主题的关联".format(', '.join(focus_areas)))
    
    # 4. 常见标题词汇建议
    style_analysis = journal_info.get('style_analysis', {})
    common_words = style_analysis.get('common_title_words', [])
    if common_words:
        suggestions.append("- 该期刊近期文章标题常用词汇：{}，可以考虑在标题或摘要中使用类似术语".format(', '.join(common_words[:5])))
    
    # 5. 写作风格建议
    suggestions.append("- 建议使用简洁、直接的学术语言，避免过度修饰")
    suggestions.append("- 建议突出研究的创新点和实际意义")
    suggestions.append("- 建议使用具体的数据或定量描述，而非笼统的定性描述")
    
    # 生成建议报告
    report = []
    report.append("# 摘要润色建议")
    report.append("")
    report.append(f"**目标期刊**: {journal_info.get('name', '未知')}")
    report.append("")
    
    if journal_info.get('aim_scope'):
        report.append("## 期刊 Aim & Scope")
        report.append("")
        report.append(journal_info['aim_scope'][:500] + "...")
        report.append("")
    
    report.append("## 润色建议")
    report.append("")
    for suggestion in suggestions:
        report.append(suggestion)
    report.append("")
    
    report.append("## 注意事项")
    report.append("")
    report.append("- 以上建议基于期刊公开信息和近期发表文章的分析")
    report.append("- 具体投稿时请参考期刊的 Author Guidelines")
    report.append("- 建议阅读 2-3 篇该期刊近期发表的相似主题文章，学习其写作风格")
    
    return "\n".join(report)


# 便捷函数
async def learn_and_suggest(
    journal_name: str,
    abstract: str,
    title: str = "",
) -> str:
    """
    学习期刊并给出摘要润色建议
    
    Args:
        journal_name: 期刊名称
        abstract: 原始摘要
        title: 论文标题
    
    Returns:
        str: 润色建议报告
    """
    learner = JournalLearner()
    journal_info = await learner.learn_journal(journal_name)
    return suggest_abstract_revision(abstract, journal_info, title)
