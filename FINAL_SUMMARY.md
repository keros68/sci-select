# sci-aiselect 完全版 - 最终总结

## 功能概述

sci-aiselect 是一个增强版的期刊选择助手，它结合了多个出版社的 Journal Finder 和 AI 匹配功能，提供更全面、更准确的期刊推荐。

## 已实现功能

### ✅ 1. 文件提取
- 支持从 Word (.docx) 和 PDF 文件提取标题、摘要和关键词
- 自动识别论文结构

### ✅ 2. Journal Finder 初筛
- **Elsevier** Journal Finder ✅
- **Wiley** Journal Finder ✅
- **Taylor & Francis** Journal Suggester ✅
- **Springer** Journal Finder ✅
- **Web of Science** Master Journal List ✅

### ✅ 3. AI 智能匹配
- 论文特征推断（研究方向、主题词）
- LetPub 候选期刊搜索
- 期刊指标聚合（LetPub + OpenAlex）
- 智能排序和分带
- Journal Finder 结果作为权重参考

### ✅ 4. 意向期刊学习
- 查找期刊官网
- 提取 aim and scope
- 分析最近发表的文章
- 提供摘要润色建议

### ✅ 5. 灵活重新匹配
- 不满意时可以重新进行 AI 匹配
- 这次不参考 Journal Finder 结果

### ✅ 6. 交互式脚本
- 交互式选择输入方式
- 交互式选择操作

## 使用方法

### 方法 1: 交互式模式（推荐）
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 interactive.py
```

### 方法 2: 从文件提取
```python
import sys
sys.path.insert(0, '/Users/alvis/.hermes/skills/sci-aiselect/scripts')
from full_workflow import extract_and_select
print(extract_and_select("path/to/paper.pdf"))
```

### 方法 3: 手动输入
```python
import sys
sys.path.insert(0, '/Users/alvis/.hermes/skills/sci-aiselect/scripts')
from full_workflow import quick_select
print(quick_select(
    "Your paper title",
    "Your paper abstract...",
    ["keyword1", "keyword2"]
))
```

### 方法 4: 期刊学习
```python
import sys
sys.path.insert(0, '/Users/alvis/.hermes/skills/sci-aiselect/scripts')
import asyncio
from journal_learner import learn_and_suggest
result = asyncio.run(learn_and_suggest(
    "Journal of Hydrology",
    "Your abstract here...",
    "Your title here"
))
print(result)
```

## 测试结果示例

### 论文：Glacial lake systems are redefining risk in a changing Himalayan cryosphere

**Journal Finder 初筛结果：**
- Elsevier: 10 个期刊
- Wiley: 6 个期刊
- Taylor & Francis: 9 个期刊
- Springer: 10 个期刊
- WOS: 10 个期刊
- 总共 45 个期刊

**AI 智能匹配结果：**
- 识别方向：地球科学/自然地理学、环境科学与生态学/水资源、地球科学/遥感
- 命中主题：hydrology, glacial, lake, hazard, remote sensing, climate change, himalaya, sediment

**最终推荐（Top 10）：**
1. Journal of Hydrology（冲刺，IF=6.3，1区）
2. Nature Geoscience（冲刺，IF=16.1，1区）
3. Egyptian Journal Of Remote Sensing And Space Sciences（稳妥，IF=7.8，2区）
4. Global and Planetary Change（稳妥，IF=4，2区）
5. Nature Climate Change（冲刺，IF=27.1，1区）
6. Ieee Geoscience And Remote Sensing Magazine（冲刺，IF=9.0，1区）
7. Geophysical Research Letters（稳妥，IF=4.6，2区）
8. Geocarto International（稳妥，IF=6.9，3区）
9. Water Resources Research（稳妥，IF=5，2区）
10. Hydrological Processes（保底，IF=2.9，3区）

## 项目结构

```
~/.hermes/skills/sci-aiselect/
├── scripts/
│   ├── journal_finders/
│   │   ├── __init__.py          # 模块入口
│   │   ├── base.py              # 基类
│   │   ├── elsevier.py          # Elsevier
│   │   ├── wiley.py             # Wiley
│   │   ├── taylor_francis.py    # Taylor & Francis
│   │   ├── springer.py          # Springer
│   │   └── wos.py               # Web of Science
│   ├── full_workflow.py         # 完整流程
│   ├── journal_learner.py       # 期刊学习和摘要润色
│   ├── select_journals.py       # AI 匹配
│   ├── journal_metrics.py       # 期刊指标
│   └── letpub_client.py         # LetPub 客户端
├── interactive.py               # 交互式脚本
├── SKILL.md                     # 技能文档
└── ...
```

## 依赖

```bash
pip install playwright requests beautifulsoup4 pymupdf python-docx
playwright install chromium
```

## 联系方式

如有问题或建议，请联系开发者。

## 许可证

MIT License
