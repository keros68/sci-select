#!/usr/bin/env python3
"""
Cookies 导出工具

帮助用户从浏览器导出 cookies，用于 Journal Finder 访问。

使用方法：
1. 运行此脚本
2. 在打开的浏览器中登录网站
3. 登录完成后按 Enter 键
4. Cookies 将自动保存

支持的网站：
- elsevier: Elsevier Journal Finder
- wiley: Wiley Journal Finder
- taylor_francis: Taylor & Francis Journal Suggester
- springer: Springer Journal Finder
- wos: Web of Science Master Journal List
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from cookies_manager import get_cookie_manager


# 网站配置
SITES = {
    'elsevier': {
        'name': 'Elsevier Journal Finder',
        'url': 'https://journalfinder.elsevier.com/',
        'login_url': 'https://www.elsevier.com/',
        'description': 'Elsevier Journal Finder 用于搜索 Elsevier 旗下的期刊',
    },
    'wiley': {
        'name': 'Wiley Journal Finder',
        'url': 'https://www.wiley.com/en-ie/journal-finder/abstract/?type=match',
        'login_url': 'https://www.wiley.com/',
        'description': 'Wiley Journal Finder 用于搜索 Wiley 旗下的期刊',
    },
    'taylor_francis': {
        'name': 'Taylor & Francis Journal Suggester',
        'url': 'https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/',
        'login_url': 'https://www.tandfonline.com/',
        'description': 'Taylor & Francis Journal Suggester 用于搜索 T&F 旗下的期刊',
    },
    'springer': {
        'name': 'Springer Journal Finder',
        'url': 'https://link.springer.com/journals',
        'login_url': 'https://link.springer.com/',
        'description': 'Springer Journal Finder 用于搜索 Springer/Nature 旗下的期刊',
    },
    'wos': {
        'name': 'Web of Science Master Journal List',
        'url': 'https://mjl.clarivate.com/home',
        'login_url': 'https://www.webofscience.com/',
        'description': 'Web of Science Master Journal List 用于搜索 SCI/SSCI 期刊',
    },
}


async def export_cookies_with_playwright(source: str, headless: bool = False):
    """
    使用 Playwright 导出 cookies
    
    Args:
        source: 网站来源
        headless: 是否无头模式
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("错误：需要安装 playwright")
        print("请运行：pip install playwright && playwright install chromium")
        return False
    
    if source not in SITES:
        print(f"错误：不支持的网站 '{source}'")
        print(f"支持的网站：{', '.join(SITES.keys())}")
        return False
    
    site = SITES[source]
    print(f"\n{'='*60}")
    print(f"导出 {site['name']} 的 Cookies")
    print(f"{'='*60}")
    print(f"\n说明：{site['description']}")
    print(f"\n步骤：")
    print(f"1. 浏览器将打开 {site['url']}")
    print(f"2. 如果需要登录，请点击登录按钮并完成登录")
    print(f"3. 登录完成后，回到此窗口按 Enter 键")
    print(f"4. Cookies 将自动保存")
    
    input("\n按 Enter 键打开浏览器...")
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 访问网站
        print(f"\n正在打开 {site['url']}...")
        await page.goto(site['url'], wait_until='networkidle')
        
        # 等待用户登录
        print("\n浏览器已打开。")
        print("如果需要登录，请在浏览器中完成登录。")
        input("登录完成后，按 Enter 键继续...")
        
        # 获取 cookies
        print("\n正在获取 cookies...")
        cookies = await context.cookies()
        
        # 保存 cookies
        cookie_manager = get_cookie_manager()
        cookie_manager.save_cookies(source, cookies)
        
        # 关闭浏览器
        await browser.close()
        
        print(f"\n✓ 成功保存 {len(cookies)} 个 cookies")
        return True


def export_cookies_manual(source: str):
    """
    手动导出 cookies（从浏览器扩展导出）
    
    Args:
        source: 网站来源
    """
    if source not in SITES:
        print(f"错误：不支持的网站 '{source}'")
        print(f"支持的网站：{', '.join(SITES.keys())}")
        return False
    
    site = SITES[source]
    print(f"\n{'='*60}")
    print(f"手动导出 {site['name']} 的 Cookies")
    print(f"{'='*60}")
    print(f"\n步骤：")
    print(f"1. 在浏览器中访问 {site['url']}")
    print(f"2. 如果需要登录，请先登录")
    print(f"3. 安装浏览器扩展 'EditThisCookie' 或 'Cookie-Editor'")
    print(f"4. 点击扩展图标，选择 '导出' 或 'Export'")
    print(f"5. 将导出的内容保存到文件")
    print(f"6. 输入文件路径")
    
    filepath = input("\n请输入 cookies 文件路径：").strip()
    
    if not filepath:
        print("错误：未输入文件路径")
        return False
    
    # 处理路径
    filepath = filepath.strip('"').strip("'")
    filepath = os.path.expanduser(filepath)
    
    if not os.path.exists(filepath):
        print(f"错误：文件不存在: {filepath}")
        return False
    
    # 导入 cookies
    cookie_manager = get_cookie_manager()
    success = cookie_manager.import_from_browser_export(filepath, source)
    
    if success:
        cookies = cookie_manager.load_cookies(source)
        print(f"\n✓ 成功导入 {len(cookies)} 个 cookies")
    else:
        print("\n✗ 导入失败")
    
    return success


def list_cookies():
    """列出所有保存的 cookies"""
    cookie_manager = get_cookie_manager()
    cookies_list = cookie_manager.list_cookies()
    
    if not cookies_list:
        print("\n没有保存的 cookies")
        return
    
    print(f"\n{'='*60}")
    print("已保存的 Cookies")
    print(f"{'='*60}")
    
    for item in cookies_list:
        print(f"\n来源: {item['source']}")
        print(f"  保存时间: {item['saved_at']}")
        print(f"  过期时间: {item['expires_at']}")
        print(f"  Cookie 数量: {item['cookie_count']}")


def delete_cookies(source: str):
    """删除指定来源的 cookies"""
    cookie_manager = get_cookie_manager()
    success = cookie_manager.delete_cookies(source)
    
    if success:
        print(f"\n✓ 已删除 {source} 的 cookies")
    else:
        print(f"\n✗ 未找到 {source} 的 cookies")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Journal Finder Cookies 导出工具")
    print("="*60)
    
    while True:
        print("\n请选择操作：")
        print("1. 自动导出 cookies（使用 Playwright）")
        print("2. 手动导入 cookies（从浏览器扩展）")
        print("3. 查看已保存的 cookies")
        print("4. 删除 cookies")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-4): ").strip()
        
        if choice == '0':
            break
        
        elif choice == '1':
            print("\n支持的网站：")
            for i, (key, site) in enumerate(SITES.items(), 1):
                print(f"  {i}. {site['name']} ({key})")
            
            source = input("\n请输入网站名称或编号：").strip()
            
            # 尝试解析为编号
            try:
                idx = int(source) - 1
                source = list(SITES.keys())[idx]
            except (ValueError, IndexError):
                pass
            
            asyncio.run(export_cookies_with_playwright(source))
        
        elif choice == '2':
            print("\n支持的网站：")
            for i, (key, site) in enumerate(SITES.items(), 1):
                print(f"  {i}. {site['name']} ({key})")
            
            source = input("\n请输入网站名称或编号：").strip()
            
            # 尝试解析为编号
            try:
                idx = int(source) - 1
                source = list(SITES.keys())[idx]
            except (ValueError, IndexError):
                pass
            
            export_cookies_manual(source)
        
        elif choice == '3':
            list_cookies()
        
        elif choice == '4':
            print("\n支持的网站：")
            for i, (key, site) in enumerate(SITES.items(), 1):
                print(f"  {i}. {site['name']} ({key})")
            
            source = input("\n请输入网站名称或编号：").strip()
            
            # 尝试解析为编号
            try:
                idx = int(source) - 1
                source = list(SITES.keys())[idx]
            except (ValueError, IndexError):
                pass
            
            delete_cookies(source)
        
        else:
            print("无效选项，请重新输入")


if __name__ == '__main__':
    main()
