# sci-AIselect

Paper-to-journal selection assistant. Combines publisher Journal Finders, LetPub expanded search, and innovation-driven quality assessment to recommend journals for SCI/SCIE/ESCI/SSCI submissions.

## How It Works

### Three-Layer Signal Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Journal Finder 初判 (5 publishers)            │
│  → 确定论文级别：breakthrough / high / solid            │
│  → 不限制最终候选池                                      │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 扩展选刊 (all publishers)                      │
│  → LetPub 搜索（所有出版社，含 ESCI）                    │
│  → 跨学科顶级期刊池（NSR, Nature, Science, PNAS）        │
│  → 文献检索校准（类似论文发在什么期刊）                   │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 创新性微调 (regex patterns)                    │
│  → 检测发现型创新（倍数变化、机制发现、反直觉结果）       │
│  → 仅用于微调，不推翻 Layer 1                           │
└─────────────────────────────────────────────────────────┘
```

**核心原则：Journal Finder 用于初判论文级别，最终选刊不限于这五个出版社。**

### Layer 1: Journal Finder 初判

5 个出版社的 Journal Finder 并行运行，各自独立评估论文：

| Publisher | URL | Coverage |
|-----------|-----|----------|
| Elsevier | journalfinder.elsevier.com | ~4000 journals |
| Wiley | wiley.com/journal-finder | ~2000 journals |
| Taylor & Francis | tandfonline.com/journal-suggester | ~3000 journals |
| Springer | link.springer.com/journals | ~3000 journals |
| Web of Science | mjl.clarivate.com | ~21000 journals |

每个 Finder 返回排序结果，通过排序模式推断论文级别：
- **多数 #1 是 Nature 级** → breakthrough
- **多数 #1 是高影响力期刊** → high
- **多数 #1 是区域/专业期刊** → solid
- **出版社分歧** → 参考创新性评分

### Layer 2: 扩展选刊

初判确定论文级别后，从以下来源扩展候选池：

**LetPub 搜索**（覆盖所有出版社）：
- 不限 SCIE（包含 ESCI 期刊）
- 每个学科分类取 15 个候选
- 覆盖 AGU、Copernicus、MDPI、IEEE、Frontiers 等 Journal Finder 未覆盖的出版社

**跨学科顶级期刊池**（高质量论文自动加入）：
- National Science Review (IF~20)
- Nature / Science (IF~60)
- PNAS (IF~10)
- Nature Communications (IF~16)
- Nature Geoscience / Nature Climate Change / Nature Sustainability 等

这些期刊永远不会出现在 Journal Finder 或 LetPub 分类搜索中，但确实发表高质量的跨学科研究。

**Aim & Scope 语义匹配**：
- 将论文标题/摘要中的关键词与期刊名/领域做交叉匹配
- 例如：论文标题含 "Indicators" → 匹配 Environmental and Sustainability Indicators
- 每项匹配 +8 分，封顶 30 分

### Layer 3: 创新性微调

通过正则模式检测摘要中的创新信号：

| 类型 | 模式示例 | 分值 |
|------|---------|------|
| 明确声明 | "addresses this gap", "for the first time" | 35-40 |
| 填补空白 | "little is known" + "this study" | 35 |
| 关键差异发现 | "in stark contrast", "remarkably" | 25 |
| 前兆检测成功 | "robustly detected ... years in advance" | 30 |
| 倍数级变化 | "5-fold increase" | 25 |
| 可比自然过程 | "comparable to alpine glaciation" | 20 |
| 空间迁移趋势 | "migrating upslope" | 20 |

创新性评分仅用于微调论文级别（≥50 分可从 solid 提升到 solid_high），不推翻 Journal Finder 的判断。

### ESCI 处理

ESCI（Emerging Sources Citation Index）期刊不再被无条件惩罚：
- ESCI + JCR Q1/Q2 → 不扣分（如 ESI, IF=5.6, JCR Q1）
- ESCI 无 Q1/Q2 分区 → 扣 10-12 分

## Installation

### Prerequisites

```bash
# Python 3.11+
pip install playwright requests beautifulsoup4 pymupdf python-docx
playwright install chromium
```

### As a Skill (Hermes / Claude Code / Codex)

The skill is managed by skills-manager. Symlinks are automatically synced to all agents:

```
~/.hermes/skills/sci-aiselect  →  ~/.skills-manager/skills/sci-aiselect
~/.claude/skills/sci-aiselect  →  ~/.skills-manager/skills/sci-aiselect
~/.codex/skills/sci-aiselect   →  ~/.skills-manager/skills/sci-aiselect
```

### Standalone

```bash
git clone https://github.com/douxy1994/sci-AIselect.git
cd sci-AIselect
pip install -r requirements.txt
playwright install chromium
```

## Usage

### Quick Select (Python API)

```python
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select

title = "Your paper title"
abstract = "Your paper abstract..."
keywords = ["keyword1", "keyword2"]

print(quick_select(title, abstract))
```

### From File (PDF / Word)

```python
import sys
sys.path.insert(0, 'scripts')
from full_workflow import extract_and_select

print(extract_and_select("path/to/paper.pdf"))
```

### Interactive Mode

```bash
python3 interactive.py
```

### Journal Learning (Abstract Revision)

```python
import sys, asyncio
sys.path.insert(0, 'scripts')
from journal_learner import learn_and_suggest

result = asyncio.run(learn_and_suggest(
    "Journal of Hydrology",
    "Your abstract here...",
    "Your title here"
))
print(result)
```

### Journal Finder Only

```python
import sys
sys.path.insert(0, 'scripts')
from journal_finders import search_all_journal_finders

results = search_all_journal_finders(title, abstract, keywords, config)
for r in results[:10]:
    print(f"{r['journal_name']} (匹配度: {r['match_score']:.2f})")
```

## Output Format

```
# sci-aiselect 选刊建议：Your Paper Title

**识别方向**：地球科学/自然地理学；环境科学与生态学/环境科学
**命中主题**：glacial, hazard, climate change
**论文档次**：扎实偏高质量研究（各出版社 #1 推荐：EPSL, GRL, Nature Geoscience）
**创新性评分**：65/100
  + 倍数级变化 (25分)
  + 可比自然过程 (20分)
  + 空间迁移趋势 (20分)

## 快速决策表
| 期刊 | 建议 | 梯度 | IF | 分区 | 收录 |
|---|---|---|---|---|---|
| National Science Review | 推荐 | 冲刺 | 20.0 | 1区 | SCIE |
| Communications Earth & Environment | 推荐 | 稳妥 | 8.9 | 1区 | SCIE |
| ... | ... | ... | ... | ... | ... |
```

## Scoring Formula

```
total_score = fit_score + quality_score × tier_scale - risk_penalty + aim_scope_bonus
```

| Component | Range | Source |
|-----------|-------|--------|
| `fit_score` | 0-32 | Journal Finder match (20) + consensus bonus (12) + topic match (10) |
| `quality_score` | 0-43 | Partition (18) + IF (15) + h-index (8), scaled by tier |
| `tier_scale` | 0.7-1.0 | breakthrough=1.0, high=0.95, solid_high=0.85, solid=0.7 |
| `risk_penalty` | 0-60 | Warning (60) + ESCI without Q1/Q2 (10) + unconfirmed SCI (30) |
| `aim_scope_bonus` | 0-30 | Journal name/field keyword match with paper (8 per match) |

## Project Structure

```
sci-AIselect/
├── scripts/
│   ├── journal_finders/         # 5 publisher Journal Finders
│   │   ├── base.py              # Base class with Playwright automation
│   │   ├── elsevier.py
│   │   ├── wiley.py
│   │   ├── taylor_francis.py
│   │   ├── springer.py
│   │   └── wos.py
│   ├── full_workflow.py         # Main workflow (3-layer architecture)
│   ├── select_journals.py       # Standalone AI selector
│   ├── journal_learner.py       # Journal learning + abstract revision
│   ├── journal_metrics.py       # LetPub + OpenAlex metrics
│   ├── letpub_client.py         # LetPub advanced search
│   ├── recommend.py             # Backward-compatible wrappers
│   └── cookies_manager.py       # Cookie persistence
├── assets/
│   └── journal_cache.json       # Cached journal metrics
├── references/
│   ├── data-sources.md
│   ├── journal-finder-automation.md
│   └── journal-finder-api-notes.md
├── interactive.py               # Interactive CLI
├── SKILL.md                     # Skill documentation (agent-facing)
├── README.md                    # This file
└── requirements.txt
```

## License

MIT
