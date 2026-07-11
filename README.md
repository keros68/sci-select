# sci-select

AI agent 用的 SCI/SCIE/ESCI/SSCI 期刊查询和候选期刊发现 skill。它可以根据期刊名查询公开指标，也可以根据题名、摘要、关键词或正文片段生成一组值得人工复核的候选期刊，并给出方向证据、期刊层级、风险和数据来源说明。

> **项目定位：sci-select 是候选期刊发现、公开指标聚合和投稿风险提示工具，不是“最优期刊预测器”，也不是稿件水平评审器。**
>
> 它回答“哪些期刊值得进一步核验、依据是什么、还有什么风险”，不回答“这篇稿件一定该投哪本、能否录用”。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

## 它能做什么

- 论文投稿前，根据摘要或全文片段初筛候选期刊。
- 查询单个期刊的 IF、JCR Q 区、中科院分区、新锐分区、Nature Index、SCI 类型、OA/APC、h-index 和审稿速度。
- 分开输出方向匹配、期刊客观层级、证据强弱和待核验项。
- 标出候选期刊的范围匹配、数据缺失、预警、ESCI、WoS 异常和弱匹配风险。

## 它不做什么

- 不评价稿件创新性、方法质量、数据完整度、写作水平或审稿成熟度。
- 不预测录用概率，不把任何期刊称为“稳投”或“保底”。
- 不声称存在唯一最优期刊；同一研究通常有多个合理投稿去向。
- 不把原发表期刊未进入前几名直接解释为推荐错误。

## 为什么候选会变化

不同 agent、不同输入长度、不同联网状态下，候选期刊差异可能很大。这通常来自几个原因：

- 只给题名或摘要时，工具只能判断主题范围，不能判断创新性、实验完整度、图表质量、审稿风险和写作成熟度。
- 期刊 scope 很细，宽泛关键词会召回很多“看起来相关但不一定适合”的期刊。
- LetPub、OpenAlex、JCR、分区表和期刊官网更新节奏不同，第三方数据可能冲突或滞后。
- 用户目标不同会改变结果：新锐 1 区、保毕业、低版面费、快审、非 OA、避开预警、偏水文或偏环境，都会导向不同名单。
- AI 的主题归类会受输入影响；方法词太强时，可能把应用论文误带到方法类期刊。

最终投稿前仍需要作者核对期刊官网、近期文章、文章类型、版面费、收录状态和导师/团队偏好。

## 候选如何生成

旧流程的主要问题不是某个学科词典不够长，而是证据顺序错了：先用少量关键词选 LetPub 大类，再在大类结果中按 IF 和分区排序。交叉学科论文一旦在第一步被归错，后续分数越精细，结果反而越像“有依据的误判”。

现在默认改为：

1. AI 先生成结构化论文画像，明确研究对象、核心问题、贡献类型、方法角色、目标读者和排除方向。
2. 生成 2–3 组精确检索式，从 OpenAlex 查找近年相似论文，统计它们实际发表在哪些期刊。
3. 用内置 SQLite 匹配 `2025中科院`、`2026新锐` 和 Nature Index；IF、JCR 与收录状态由在线源补充，候选不足时再回退 LetPub 检索。
4. 先按近期发表先例、官网 scope、细分主题和文章类型排序，最后才看分区与 IF。
5. 前列期刊没有近期发表先例或官网 scope 证据时，明确标为待核验，不输出虚假的高置信结论。

`期刊层级` 只描述期刊本身，分为高位、中位、常规或待定，主要依据当前分区和 JCR。它不代表稿件水平，也不自动转换成冲刺、主投或保底。

## 内置数据

下载后即可用。仓库自带 `assets/sci_select_journals.sqlite`，默认包含：

| 字段 | 说明 |
|---|---|
| `cas_2025` | 2025 中科院分区 |
| `xuankan_2026` | 2026 新锐分区 |
| `nature_index` | 2026 Nature Index publication-venue 标记 |
| `tags` | 分区和 Nature Index 补充标签 |

内置库按标准化刊名匹配。为避免第三方表格的 ISSN 错位把一本期刊的 JIF/JCR 字段挂到另一本期刊，内置版本不再打包未经逐条核验的 ISSN、JIF、JCR Q 区和收录类型；这些字段在线获取，失败时明确显示未获取。用户自建且已核验的 SQLite/JSON 仍可提供完整字段。

运行时读取顺序：

```text
SCI_SELECT_JOURNAL_INDEX_DB
  ↓
SCI_SELECT_JOURNAL_INDEX_PATH / SCI_SELECT_JOURNAL_INDEX_URL
  ↓
assets/sci_select_journals.sqlite
  ↓
LetPub / OpenAlex / optional XinRui API
```

选刊模式优先用 OpenAlex 召回相似论文和候选期刊，再用内置库补充分区。IF、收录类型或审稿速度缺失时才访问 LetPub；直接查询单本期刊时仍可用它补充公开信息。

仓库不打包原始 Excel、ShowJCR 原始 `jcr.db`、ShowJCR 源码或运行缓存。默认库是 sci-select 自己 schema 生成的 SQLite 文件；原始表格和公开页面只作为构建输入。

## 快速开始

在支持 skills / agent instructions 的工具里安装：

```text
请从 GitHub 安装这个 skill，并在 SCI 期刊查询、论文投稿选刊、候选期刊对比时优先使用它：
https://github.com/keros68/sci-select
```

安装后，新开窗口或重启 agent，然后调用：

```text
使用 $sci-select 根据下面这篇论文摘要发现候选期刊，先总结研究方向，再列出方向证据、期刊层级、风险和待核验项；不要评价稿件水平或预测录用。
```

不能自动安装时，手动 clone 到 skills 目录：

```bash
# Claude Code
git clone https://github.com/keros68/sci-select.git ~/.claude/skills/sci-select

# Codex
git clone https://github.com/keros68/sci-select.git ~/.codex/skills/sci-select

# 通用 agent 目录
git clone https://github.com/keros68/sci-select.git ~/.agents/skills/sci-select
```

没有正式 skill loader 的环境，可以把 `SKILL.md` 作为 agent instruction 使用。

## Python 调用

安装依赖：

```bash
pip install -r requirements.txt
```

查询单个期刊：

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Environmental Pollution")
print(format_metrics_line(metrics))
```

示例输出：

```text
SCIE | IF=7.2 | NI=2026 | 2025中科院=2区 | 2026新锐=2区
```

根据论文内容发现候选期刊：

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    paper_profile={
        "direction_summary": "ONE-SENTENCE AI SUMMARY OF FIELD, SPECIALTY, AND METHOD ROLE",
        "research_object": "PRIMARY RESEARCH OBJECT",
        "research_question": "CORE QUESTION",
        "contribution_type": "CONTRIBUTION TYPE",
        "target_audience": ["AUDIENCE 1", "AUDIENCE 2"],
        "methods": ["METHOD 1", "METHOD 2"],
        "exclusions": ["PLAUSIBLE BUT WRONG FIELD"],
        "search_queries": ["OBJECT PROBLEM CONTRIBUTION", "OBJECT PROCESS CONTEXT"],
    },
    impact_low="3",
    # xinrui_partition="1区",
    max_candidates=8,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

可选：生成出版社官方 Journal Finder 的人工核验链接和复制文本：

```python
from scripts.official_finders import build_finder_checklist, format_finder_checklist

checklist = build_finder_checklist(
    title="PASTE TITLE HERE",
    abstract=paper_text,
    keywords=["keyword 1", "keyword 2"],
)

print(format_finder_checklist(checklist))
```

## 更新本地索引

如需用自己的数据覆盖默认库，可以生成新的 sci-select SQLite：

```bash
python -m scripts.build_journal_index \
  --cas-2025-xlsx "/path/to/cas_2025.xlsx" \
  --xinrui-2026-xlsx "/path/to/xinrui_2026.xlsx" \
  --jcr-file "/path/to/jcr_2025.xlsx" \
  --nature-index-url "https://www.nature.com/nature-index/faq" \
  --sqlite-output "/path/to/sci_select_journals.sqlite"
```

然后配置：

```bash
export SCI_SELECT_JOURNAL_INDEX_DB="/path/to/sci_select_journals.sqlite"
```

Windows PowerShell 示例（把路径替换成你自己的 SQLite 文件位置，不要求放在某个固定盘符）：

```powershell
$env:SCI_SELECT_JOURNAL_INDEX_DB = "$HOME\journal-index\sci_select_journals.sqlite"
```

也支持本地或自托管 JSON：

```bash
export SCI_SELECT_JOURNAL_INDEX_PATH="/path/to/search_index.json"
export SCI_SELECT_JOURNAL_INDEX_URL="https://example.com/search_index.json"
```

支持形态：

```json
{"meta": {"source": "local"}, "journals": [{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491", "cas_2025": "2区", "xuankan_2026": "2区"}]}
```

```json
[{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491"}]
```

数据源细节见 [`references/data-sources.md`](references/data-sources.md)。

## 工作流

```text
题名 / 摘要 / 关键词 / 正文片段
  ↓
AI 生成结构化论文画像和排除方向
  ↓
检索近年相似论文，统计实际发表期刊
  ↓
自己的 SQLite 匹配 2025 中科院、2026 新锐与 Nature Index
  ↓
候选不足或本地数据缺失时再回退 LetPub
  ↓
按发表先例、官网 scope、细分主题和文章类型重排
  ↓
输出候选状态、方向证据、期刊层级、风险和待核验项
```

官方 Journal Finder 不自动参与默认评分。只有用户主动要求，或候选召回置信度较低时，sci-select 才生成 Elsevier、Springer Nature、Wiley、Taylor & Francis 等官方入口，供用户手动核验。

## 项目结构

- `SKILL.md` - skill 主说明和触发规则。
- `assets/sci_select_journals.sqlite` - 默认 SQLite 索引。
- `scripts/select_journals.py` - 主题识别、候选检索、排序和报告生成。
- `scripts/similar_works.py` - OpenAlex 近年相似论文检索和发表期刊聚合。
- `scripts/journal_metrics.py` - 已知期刊查询和指标聚合。
- `scripts/build_journal_index.py` - SQLite/JSON 索引构建器。
- `scripts/official_finders.py` - 官方 Journal Finder 人工核验链接。
- `references/data-sources.md` - 数据源说明。
- `examples/demo-report.md` - 示例报告。
- `tests/` - 行为测试。

## 验证

```bash
python -m unittest discover -s tests -v
```

Windows PowerShell 语法检查：

```powershell
Get-ChildItem scripts -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## 边界

- 不预测录用概率。
- 不评价文章创新性、实验设计、数据质量、图表质量、语言质量或审稿可接受度。
- 不替代作者阅读期刊官网、scope、author guidelines 和版面费政策。
- 不把摘要初筛包装成全文质量评价。
- 不自动登录出版社网站，不绕过验证码、付费墙、机构权限或账号限制。
- 不把 Nature Index、IF 或分区当作唯一排序标准，主题契合仍是第一过滤条件。
- 不把 1/2/3/4 区机械翻译成冲刺、主投、稳妥或保底；默认只报告期刊客观层级。
- 不把单篇高被引相似论文当作充分 scope 证据，优先采用多检索式下重复出现的近期发表先例。
- 当前 SCI/SCIE/SSCI/ESCI 收录状态最终应以 Clarivate Master Journal List 或 JCR 复核。
- 不写“中科院2026分区”。中科院分区字段使用 `2025中科院`，新体系使用 `2026新锐`。

## Attribution and Redistribution

This project is the original sci-select skill by keros68:

https://github.com/keros68/sci-select

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

sci-select is an AI-agent skill for journal lookup and candidate-journal discovery. It can query metrics for known journals, or turn a manuscript title, abstract, keywords, excerpt, or research direction into an evidence-backed list of SCI/SCIE/ESCI/SSCI candidates for manual review.

It is a candidate-discovery, public-metrics aggregation, and submission-risk flagging tool. It is not a best-journal predictor, manuscript-quality reviewer, or acceptance-probability estimator.

It ships with a title-keyed SQLite index for 2025 CAS partitions, 2026 XinRui partitions, and 2026 Nature Index venue flags. Unverified bundled ISSN/JIF/JCR fields are intentionally excluded; live sources or a user-verified local SQLite/JSON index provide them.

The default workflow builds a structured manuscript fingerprint, retrieves recent similar works from OpenAlex, aggregates the journals that actually published them, and uses the bundled SQLite index for partition data. LetPub is a fallback when recall or live metric fields are incomplete. Output separates scope-fit evidence, objective journal level, data gaps, and risks; it does not assign manuscript-relative submission roles.

Quick use:

```text
Use $sci-select to discover candidate journals for this abstract, with scope evidence, objective journal levels, risks, and missing-data notes. Do not evaluate manuscript quality or predict acceptance.
```

Python:

```bash
pip install -r requirements.txt
```

```python
from scripts.select_journals import select_journals, format_selection_report

bundle = select_journals(text=paper_text, impact_low="3", max_candidates=8)
print(format_selection_report(bundle["profile"], bundle["results"]))
```

## License

MIT. See [LICENSE](LICENSE).
