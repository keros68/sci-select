#!/usr/bin/env python3
"""
sci-aiselect 交互式脚本

功能：
1. 从文件提取标题和摘要
2. Journal Finder 初筛
3. AI 匹配（结合 Journal Finder 结果作为权重参考）
4. 提供 10 个综合选择
5. 意向期刊学习和摘要润色
6. 不满意时重新匹配
"""
import sys
import os
import asyncio

# 添加 scripts 目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from full_workflow import (
    extract_from_file,
    select_journals_with_finder,
    format_full_report,
)
from journal_learner import learn_and_suggest


def main():
    """主函数"""
    print("\n" + "="*70)
    print("sci-aiselect 期刊选择助手")
    print("="*70)
    
    # 步骤 1: 获取论文信息
    print("\n请选择输入方式：")
    print("1. 从文件提取（Word 或 PDF）")
    print("2. 手动输入")
    
    choice = input("\n请输入选项 (1-2): ").strip()
    
    title = ""
    abstract = ""
    keywords = []
    
    if choice == '1':
        # 从文件提取
        file_path = input("\n请输入文件路径：").strip()
        file_path = file_path.strip('"').strip("'")
        
        try:
            title, abstract, keywords = extract_from_file(file_path)
            print(f"\n提取的标题：{title[:80]}...")
            print(f"提取的摘要：{abstract[:150]}...")
            print(f"提取的关键词：{keywords}")
        except Exception as e:
            print(f"\n文件提取失败：{e}")
            print("请手动输入论文信息。")
            choice = '2'
    
    if choice == '2':
        # 手动输入
        print("\n请输入论文信息：")
        title = input("标题：").strip()
        print("摘要（输入空行结束）：")
        abstract_lines = []
        while True:
            line = input()
            if not line:
                break
            abstract_lines.append(line)
        abstract = "\n".join(abstract_lines)
        
        keywords_input = input("关键词（逗号分隔）：").strip()
        if keywords_input:
            keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
    
    if not title and not abstract:
        print("\n错误：未提供论文信息。")
        return
    
    # 步骤 2: Journal Finder 初筛 + AI 匹配
    print("\n" + "="*70)
    print("正在进行期刊匹配...")
    print("="*70)
    
    bundle = select_journals_with_finder(
        title=title,
        abstract=abstract,
        keywords=keywords,
        use_journal_finders=True,
        max_candidates=10,
    )
    
    # 步骤 3: 显示结果
    print("\n" + "="*70)
    print("期刊推荐结果")
    print("="*70)
    print(format_full_report(bundle, title=title, show_finder_results=True))
    
    # 步骤 4: 询问用户意向
    while True:
        print("\n" + "="*70)
        print("请选择操作：")
        print("1. 选择一个意向期刊，学习其风格并获取摘要润色建议")
        print("2. 不满意，重新进行 AI 匹配（不参考 Journal Finder 结果）")
        print("3. 退出")
        
        choice = input("\n请输入选项 (1-3): ").strip()
        
        if choice == '1':
            # 用户选择意向期刊
            journal_name = input("\n请输入意向期刊名称：").strip()
            
            if journal_name:
                print(f"\n正在学习期刊：{journal_name}")
                print("（这可能需要一些时间...）")
                
                # 学习期刊并获取摘要润色建议
                suggestions = asyncio.run(learn_and_suggest(journal_name, abstract, title))
                print("\n" + suggestions)
        
        elif choice == '2':
            # 重新进行 AI 匹配
            print("\n" + "="*70)
            print("重新进行 AI 匹配（不参考 Journal Finder 结果）...")
            print("="*70)
            
            bundle = select_journals_with_finder(
                title=title,
                abstract=abstract,
                keywords=keywords,
                use_journal_finders=False,  # 不使用 Journal Finder
                max_candidates=10,
            )
            
            print("\n" + "="*70)
            print("新的期刊推荐结果")
            print("="*70)
            print(format_full_report(bundle, title=title, show_finder_results=False))
        
        elif choice == '3':
            print("\n感谢使用 sci-aiselect！")
            break
        
        else:
            print("\n无效选项，请重新输入。")


if __name__ == '__main__':
    main()
