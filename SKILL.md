---
name: sci-aiselect
description: Use when a user wants SCI, SCIE, ESCI, SSCI, or journal submission help, including paper-to-journal recommendations from a title, abstract, keywords, manuscript text, or research direction, and direct journal lookup for metrics such as IF, CAS partition, SCI type, review speed, OA/APC, h-index, and data-source notes.
---

# sci-aiselect

sci-aiselect is a journal lookup and paper-to-journal selection assistant. It combines multiple publisher Journal Finders with AI-powered matching to provide comprehensive journal recommendations.

## Features

### 1. File Extraction
Extract title, abstract, and keywords from Word (.docx) or PDF files.

### 2. Multi-Source Journal Finder
Search journals from 5 publishers simultaneously:
- Elsevier, Wiley, Taylor & Francis, Springer, Web of Science

### 3. LetPub Expanded Search
Beyond the 5 Journal Finders, search LetPub for additional candidates:
- Covers ALL publishers (AGU, Copernicus, MDPI, IEEE, Frontiers, NSR, etc.)
- Includes ESCI journals with good JCR partition
- Not limited to SCIE-only

### 4. Top-Tier Cross-Disciplinary Pool
For papers with strong innovation signals, always consider:
- **National Science Review** (IF~20, Chinese Academy of Sciences, broad scope)
- **Nature** / **Science** (IF~60, breakthrough discoveries)
- **PNAS** (IF~10, broad scope, PNAS Nexus for newer papers)
- **Nature Communications** (IF~16, broad scope)
- These journals are NEVER returned by Journal Finders or LetPub category searches, but they DO publish high-quality earth/climate/environmental science

### 4. Journal Learning and Abstract Revision
Learn about a target journal and get abstract revision suggestions.

### 5. Flexible Re-matching
If user is not satisfied, re-run AI matching without Journal Finder constraints.

## Workflow Design

### Innovation Assessment: What IS and IS NOT Innovation

**核心原则：创新不是"做了什么分析"，而是"改变了什么认知"。**

#### ✅ 真正的创新信号
1. **机制发现** — 揭示了之前未被充分认识的因果关系
   - 例："frozen lateral moraine containing dead ice" → 冻土退化是冰碛坍塌的根本原因
   - 例："sediment erosion 20× exceeds moraine collapse volume" → 侵蚀量远超预期

2. **认知改变** — 改变了领域对某类问题的理解框架
   - 例："paradigm shifts in GLOF risk management"
   - 例："wider relevance given rapid climate warming worldwide"

3. **首次方法应用** — 第一次用某种方法解决了之前无法解决的问题
   - 例："first detection of GLOF precursors 3 years in advance using optical pixel offset tracking"
   - 注意：必须是"第一次用"，不是"用了"

4. **反直觉发现** — 发现了与预期不符的结果
   - 例："in stark contrast, no discernible deformation anomalies were detected around the ice dam"

5. **显著的定量发现** — 通过数据展现的创新（不是声明，是发现本身）
   - 例："5-fold increase in annual landslide volumes" → 倍数级变化
   - 例："comparable to that of alpine glaciation" → 可比重要自然过程
   - 例："migrating upslope in the wake of retreating glaciers" → 空间迁移趋势
   - 注意：这类创新**不会用"novel"等词**，而是通过数据和对比展现

#### ❌ 不是创新（但经常被误判为创新）
1. **用了某种方法** — "using r.avaflow model"、"integrates satellite observations" → 不是创新
2. **涉及某个主题** — "compound hazard interactions"、"transboundary settings" → 不是创新
3. **描述某种现象** — "accelerated growth"、"spatially variable" → 不是创新
4. **自称为新** — "novel framework for GLOF hazard assessment"（但实际只是标准敏感性分析）→ 不一定是创新
5. **覆盖了某个区域** — "Indian Himalayan Region"、"36 glacial lakes" → 不是创新

#### 如何区分
| 问题 | 是创新 | 不是创新 |
|------|--------|---------|
| 揭示了新的物理机制？ | ✅ 冻土退化导致冰碛坍塌 | ❌ 用模型重建了溃决过程 |
| 改变了领域认知？ | ✅ GLOF 风险管理需要范式转变 | ❌ 提供了区域风险管理的参考 |
| 第一次做某件事？ | ✅ 首次提前3年检测到前兆 | ❌ 用卫星影像分析了冰湖变化 |
| 发现了反直觉的结果？ | ✅ 冰坝前无变形信号 vs 冰碛有 | ❌ 冰湖面积扩大了15% |

### Three-Layer Signal Architecture

期刊推荐基于三层信号，按可靠性排序：

#### Layer 1: Journal Finder 初判（首要，定级别）
- 5 个出版社的 Journal Finder 各自独立评估论文，给出排序
- **目的：判断论文的级别**（breakthrough / high / solid），而非提供最终候选期刊
- 如果所有出版社都把区域/专业期刊排第一 → 论文级别为 solid
- 如果多个出版社把高影响力期刊排第一 → 论文级别为 high
- **关键：初判完成后，最终选刊不限于这 5 个出版社**

#### Layer 2: 扩展选刊（核心，全覆盖）
初判确定论文级别后，从以下来源扩展候选池：
- **LetPub 搜索**：覆盖所有出版社（AGU、Copernicus、MDPI、IEEE、Frontiers 等），不限 SCIE
- **跨学科顶级期刊池**：NSR、Nature、Science、PNAS 等（永远不会出现在 Journal Finder 中）
- **期刊分布校准**：通过文献检索看类似主题的论文都发在什么期刊上

#### Layer 3: 创新性微调（辅助，可靠性低）
- 用正则模式检测摘要中的创新信号
- 仅用于极端情况的微调，不能推翻 Layer 1 的级别判断

### Agent 执行流程

```
Step 1: Journal Finder 初筛（5 个出版社并行）
        → 得到每个出版社的推荐排序

Step 2: 从排序推断论文档次
        → 多数 #1 是 Nature 级 → breakthrough
        → 多数 #1 是高影响力 → high
        → 多数 #1 是区域/专业 → solid
        → 分歧大 → 需要 Layer 2 验证

Step 3: 创新点提取 + 文献检索（当需要验证时）
        a) 从摘要提取"可能的创新点"关键词
        b) 用关键词搜索文献（web_search 或 scansci_pdf_search）
        c) 分析检索结果：
           - 创新性：类似文献多不多？
           - 期刊分布：类似文献发在什么期刊上？
        d) 根据结果调整推荐

Step 4: 最终推荐
        → 综合三层信号，给出 10 个期刊推荐
        → 每个推荐标注信号来源和置信度
```

### Submission Band Logic
| Paper Tier | Max Band | Meaning |
|---|---|---|
| breakthrough | 冲刺 | No cap — top journals are appropriate |
| high | 冲刺 | No cap — quality justards ambition |
| solid_high | 稳妥 | Conservative — don't overshoot |
| solid | 稳妥 | Conservative — match journal to solid work |

**Scope NEVER affects submission band.** A regional study with strong innovation gets "冲刺" if it deserves it.

## Quick Start

### Option 1: Interactive Mode (Recommended)
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 interactive.py
```

### Option 2: From File
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import extract_and_select
print(extract_and_select("path/to/paper.pdf"))
EOF
```

### Option 3: Manual Input
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select

title = "Your paper title"
abstract = "Your paper abstract..."
keywords = ["keyword1", "keyword2"]

print(quick_select(title, abstract, keywords))
EOF
```

### Option 4: Journal Learning
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
import asyncio
from journal_learner import learn_and_suggest

result = asyncio.run(learn_and_suggest(
    "Journal of Hydrology",
    "Your abstract here...",
    "Your title here"
))
print(result)
EOF
```

## Workflow

### Step 1: File Extraction (Optional)
If user provides a file, extract title, abstract, and keywords.

### Step 2: Journal Finder Initial Screening
Search journals from 5 publishers simultaneously.

### Step 3: AI-Powered Selection
Use AI to:
1. Infer paper profile (topics, methods, categories)
2. Search LetPub for candidate journals
3. Aggregate metrics from LetPub and OpenAlex
4. Score and rank candidates (using Journal Finder results as weight reference)
5. Assign submission bands (冲刺/稳妥/保底)

### Step 4: Present 10 Recommendations
Show top 10 journals with recommendation tier, submission band, metrics, and source.

### Step 5: User Decision
Ask user if they have a preferred journal:
- **If yes**: Learn about the journal and provide abstract revision suggestions
- **If no**: Re-run AI matching without Journal Finder constraints

### Step 6: Journal Learning (If User Selects a Journal)
1. Find journal official website
2. Extract aim and scope
3. Analyze recent articles
4. Provide abstract revision suggestions

### Step 7: Abstract Revision Suggestions
Based on journal analysis:
- Length suggestions
- Structure suggestions
- Style suggestions
- Focus area suggestions

## Configuration

### Journal Finder Configuration
```python
config = {
    'timeout': 90000,
    'retry_count': 1,
    'elsevier': {'enabled': True},
    'wiley': {'enabled': True},
    'taylor_francis': {'enabled': True},
    'springer': {'enabled': True},
    'wos': {'enabled': True},
}
```

## Required Output

For each recommendation, include:
- Tier: `推荐`, `备选`, `谨慎`, or `不推荐`
- Submission band: `冲刺`, `稳妥`, `保底`, or `谨慎`
- Metrics: IF, partition, SCI type, h-index
- Source: which Journal Finder found it

## Common Mistakes

- Do not treat method terms (ML, DL, GIS) as primary journal field
- Do not recommend journals only because IF is high
- Do not give only elite journals without quality assessment
- Always preserve a realistic submission gradient
- **Do not penalize ESCI journals unconditionally** — ESCI + JCR Q1/Q2 is a good journal; only penalize ESCI without good partition data
- **Do not limit candidates to 5 Journal Finder publishers** — use LetPub to expand coverage to all publishers (AGU, Copernicus, MDPI, IEEE, Frontiers, etc.)
- **Do not let IF ranking override topic fit** — aim & scope matching should be able to compensate for IF differences
- **"novel framework" in abstract does not equal innovation** — check if the framework is actually novel or just a standard sensitivity analysis with a new name

## Pitfalls

- Journal Finder uses Playwright, which requires Chromium browser
- First run may take longer due to browser installation
- Some websites may block automated access (e.g., Wiley)
- LetPub requests have 0.5s delay to avoid blocking
- OpenAlex API may timeout occasionally

## Verification

Run the tests:
```bash
cd ~/.hermes/skills/sci-aiselect

# Full workflow test
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select
print(quick_select(
    "Glacial lake systems are redefining risk in a changing Himalayan cryosphere",
    "Glacial lakes are expanding rapidly across the Himalaya...",
    ["glacial lakes", "GLOF", "Himalaya"]
))
EOF
```

## Dependencies

```bash
pip install playwright requests beautifulsoup4 pymupdf python-docx
playwright install chromium
```
