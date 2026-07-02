# sci-select

AI agent 期刊查询和论文投稿选刊 skill：可以根据期刊名查询公开指标，也可以根据题名、摘要、关键词、全文片段或研究方向推荐 SCI/SCIE/ESCI/SSCI 候选期刊，并输出可复查的期刊指标、匹配理由、风险提示和投稿梯度。

> 中文为主，English version below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

## 适用场景

- 论文写完后，根据摘要、关键词或全文片段初筛投稿期刊。
- 已经有目标期刊，想快速查询 IF、2025 中科院分区、2026 新锐分区、SCI 类型、OA/APC、h-index、审稿速度等信息。
- 想同时看到冲刺、稳妥、保底和谨慎选择，而不是只列高影响因子期刊。
- 需要把候选期刊的 IF、2025 中科院、2026 新锐、SCI 类型、OA/APC、h-index、审稿速度等信息放在一个报告里。
- 想让 AI agent 先做期刊范围匹配、指标聚合和风险标注，再由作者人工复核。

## 它做什么

- 根据期刊名查询公开期刊指标，并标出缺失的数据源。
- 从论文内容中识别主题、方法和候选 LetPub 学科分类。
- 区分研究对象/问题和方法词，使用细分主题证据辅助重排，避免只按高 IF 或粗分类推荐。
- 可选读取用户本地生成的统一 SQLite 索引，用于优先补充 ISSN、2025 JIF/JCR Q 区、2025 中科院分区、2026 新锐分区和预警标签。
- 也保留用户本地或自托管 JSON 索引作为轻量兼容路径。
- 使用公开 LetPub 信息检索期刊候选，并补充 IF、2025 中科院分区、2026 新锐分区、SCI/SCIE/ESCI 标签、审稿速度和预警线索。
- 可用 `xinrui_partition="1区"` 这类参数严格筛选 2026 新锐分区，避免把新锐 2 区误列进新锐 1 区名单。
- 2026 新锐分区可优先来自用户配置的本地/静态索引；未配置时解析 LetPub 公开期刊页面；`XINRUI_API_KEY` 只作为可选兜底，不是普通使用前提。
- 使用 OpenAlex 聚合 h-index、2-year mean citedness、OA 状态、APC、作品量和引用量等补充指标。
- 按主题匹配优先于影响因子的原则，对候选期刊打分和分级。
- 输出 `推荐`、`备选`、`谨慎`、`不推荐`，并进一步标记 `冲刺`、`稳妥`、`保底`、`谨慎` 投稿梯度。
- 用户主动要求时，生成 Elsevier、Springer Nature、Wiley、Taylor & Francis 等官方 Journal Finder 的人工核验链接和可复制查询文本。
- 在数据源失败或缺失时明示 `OpenAlex未获取`、`LetPub详情未获取` 等数据说明。
- 当候选列表整体匹配证据不足时，报告会提示“候选召回置信度较低”，提醒用户不要仅按 IF 或分区决策。
- 对分区表达保持区分：中科院文献情报中心已停止更新发布期刊分区表，报告中使用 `2025中科院` 和 `2026新锐` 两列，不写“中科院2026分区”。
- 对已知 WoS 收录异常期刊做风险覆盖。例如 `Science of the Total Environment` 不再按旧数据展示为正常 SCIE，而标记为 `WoS已移除/不推荐`，并提示以 Clarivate Master Journal List 复核。

## 不做什么

- 不预测录用概率，不承诺命中高影响力期刊。
- 不替代作者阅读官网 scope、author guidelines、版面费政策和最新收录状态。
- 不把只基于摘要的初筛包装成全文质量评价。
- 不绕过验证码、付费墙、机构权限或账号限制。
- 不自动登录出版社网站，也不把官方 Journal Finder 结果作为默认评分来源。
- 不抓取社区/论坛内容；投稿体验类信息不纳入本工具。
- 不随仓库打包完整第三方期刊元数据库；如需使用 JCR、中科院、新锐或 ShowJCR 数据，由用户自行准备并在本地导入为 sci-select 自己的 SQLite 索引。

## 工作流程

默认流程只使用公开指标和本地排序逻辑：

```text
题名 / 摘要 / 关键词 / 全文片段
  ↓
识别研究对象、研究问题、方法词和细分主题证据
  ↓
LetPub 公开检索召回候选期刊
  ↓
聚合可选本地索引、LetPub、OpenAlex 和可选新锐 API 指标
  ↓
按主题契合、细分 scope 证据、风险和指标重排
  ↓
输出冲刺、稳妥、保底和谨慎梯度报告
```

官方 Journal Finder 不在默认链路里自动运行。它只在两种情况下作为人工核验模块出现：

- 用户明确要求“用官方 Journal Finder 再核验一下”；
- 默认候选整体匹配证据不足，报告提示“候选召回置信度较低”。

这时 sci-select 只生成官方入口和复制文本：

```text
低置信候选 / 用户主动要求
  ↓
生成 Elsevier、Springer Nature、Wiley、Taylor & Francis 链接
  ↓
生成可复制的 Title + Abstract + Keywords
  ↓
用户手动打开官网粘贴查询
  ↓
用户可把官方结果发回，再由 sci-select 对比候选重合度和风险
```

## 使用方式

在支持 skills / agent instructions 的 agent 里，可以直接发送：

```text
请从 GitHub 安装这个 skill，并在之后需要论文投稿选刊、SCI 期刊推荐或候选期刊指标对比时优先使用它：
https://github.com/keros68/sci-select
```

安装后，重启或新开 agent 窗口测试：

```text
使用 $sci-select 根据下面这篇论文摘要推荐投稿期刊，并列出冲刺、稳妥、保底和谨慎选择。
```

如果 agent 不能自动安装 GitHub skill，可以手动 clone 到它的 skills 目录：

```bash
# Claude Code
git clone https://github.com/keros68/sci-select.git \
  ~/.claude/skills/sci-select

# Codex
git clone https://github.com/keros68/sci-select.git \
  ~/.codex/skills/sci-select

# 通用 agent 约定目录
git clone https://github.com/keros68/sci-select.git \
  ~/.agents/skills/sci-select

# 项目局部使用
git clone https://github.com/keros68/sci-select.git \
  ./.agents/skills/sci-select
```

没有正式 skill loader 的环境，也可以把 `SKILL.md` 作为 agent instruction 使用；需要了解数据来源时，再附带 `references/data-sources.md`。

## Python 直接调用

安装依赖：

```bash
pip install -r requirements.txt
```

查询单个期刊：

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Journal of Hydrology")
print(format_metrics_line(metrics))
```

默认会优先解析 LetPub 公开页面上的 2026 新锐分区。若需要用新锐 WebAPI 作为兜底，可额外配置：

```bash
export XINRUI_API_KEY="YOUR_API_KEY"
```

### 生成本地 SQLite 索引

推荐把你自己有权使用的 Excel、CSV 或 ShowJCR `jcr.db` 一次性导入为 sci-select 自己的 SQLite 索引。Excel 和 ShowJCR 只是导入输入，运行时不再依赖它们。

```bash
python -m scripts.build_journal_index \
  --cas-2025-xlsx "/path/to/cas_2025.xlsx" \
  --xinrui-2026-xlsx "/path/to/xinrui_2026.xlsx" \
  --jcr-file "/path/to/jcr_2025.xlsx" \
  --sqlite-output "/path/to/sci_select_journals.sqlite"
```

如果你本地已有 ShowJCR 风格的 `jcr.db`，也可以作为输入生成 sci-select 自己的库：

```bash
python -m scripts.build_journal_index \
  --showjcr-db "/path/to/jcr.db" \
  --sqlite-output "/path/to/sci_select_journals.sqlite"
```

然后配置：

```bash
export SCI_SELECT_JOURNAL_INDEX_DB="/path/to/sci_select_journals.sqlite"
```

Windows PowerShell：

```powershell
$env:SCI_SELECT_JOURNAL_INDEX_DB = "D:\journal-index\sci_select_journals.sqlite"
```

仓库只包含导入脚本、SQLite schema 和测试，不包含完整 JCR、中科院、新锐、ShowJCR 数据或生成后的数据库文件。

如果你已经有本地或自托管的 JSON 期刊索引，也可以让 sci-select 读取它：

```bash
export SCI_SELECT_JOURNAL_INDEX_PATH="/path/to/search_index.json"
# 或
export SCI_SELECT_JOURNAL_INDEX_URL="https://example.com/search_index.json"
```

支持两种 JSON 形态：

```json
{"meta": {"source": "local"}, "journals": [{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491", "cas_2025": "2区", "xuankan_2026": "2区"}]}
```

```json
[{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491", "cas_2025": "2区", "xuankan_2026": "2区"}]
```

识别字段包括 `title`、`issn`、`eissn`、`jif_2025`、`jcr_release_year`、`jcr_data_year`、`jcr_quartile_2025`、`if_2023`、`if_year`、`jcr_quartile`、`cas_2025`、`xuankan_2026`、`warning_latest`、`xuankan_warning`、`tags`。如果本地索引和 LetPub 的分区不一致，报告会保留本地索引值，并提示“分区来源冲突需复核”。

运行一个公开指标选刊流程：

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    impact_low="3",
    # 如果投稿目标要求“新锐1区”，取消下一行注释。
    # xinrui_partition="1区",
    max_candidates=8,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

可选：如果想再用出版社官方 Journal Finder 做人工核验，可以生成链接和复制文本：

```python
from scripts.official_finders import build_finder_checklist, format_finder_checklist

checklist = build_finder_checklist(
    title="PASTE TITLE HERE",
    abstract=paper_text,
    keywords=["keyword 1", "keyword 2"],
)

print(format_finder_checklist(checklist))
```

如果已经有本地指标记录，也可以跳过联网检索，只用排序和报告格式化逻辑：

```python
from scripts.select_journals import infer_paper_profile, rank_metric_records, format_selection_report

profile = infer_paper_profile(paper_text)
records = [
    {
        "name": "Example Journal",
        "impact_factor": "5.2",
        "partition": "2区",
        "sci_type": "SCIE",
        "field": "MATCHED JOURNAL FIELD",
        "_sources": ["letpub"],
    }
]
ranked = rank_metric_records(profile, records)

print(format_selection_report(profile, ranked))
```

## 输出内容

常见输出包括：

- 已知期刊的指标汇总；
- 识别方向和命中主题；
- 快速决策表；
- 候选期刊的推荐等级和投稿梯度；
- IF、2025 中科院、2026 新锐、SCI 类型、审稿速度、h-index、OA/APC 等指标；
- 主题匹配理由；
- 预警、ESCI、综述型期刊、弱匹配、数据缺失等风险说明；
- 数据来源缺失或失败提示。

示例报告见 [`examples/demo-report.md`](examples/demo-report.md)。

## 文件结构

- `SKILL.md` - skill 主说明和触发规则。
- `agents/openai.yaml` - 兼容运行时的 UI 元数据。
- `requirements.txt` - Python 直接调用所需依赖。
- `scripts/select_journals.py` - 主题识别、候选检索、排序和报告生成主入口。
- `scripts/journal_metrics.py` - 已知期刊查询与 LetPub + OpenAlex 指标聚合。
- `scripts/journal_index_client.py` - 可选本地/静态期刊索引读取器。
- `scripts/build_journal_index.py` - 从用户自备 Excel、CSV 或 ShowJCR SQLite 导入为 sci-select SQLite/JSON 索引。
- `scripts/official_finders.py` - 官方 Journal Finder 人工核验链接和复制文本生成。
- `scripts/letpub_client.py` - LetPub 公开页面检索客户端。
- `scripts/recommend.py` - 旧接口兼容包装。
- `references/data-sources.md` - 数据源说明。
- `examples/demo-report.md` - 示例选刊报告。
- `tests/` - 行为测试。

## 验证

```bash
python -m unittest discover -s tests -v
```

Windows PowerShell 下可以这样做语法检查：

```powershell
Get-ChildItem scripts -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## 已知局限

选刊质量取决于输入文本完整度、本地索引质量、公开网页可访问性、LetPub 页面结构、OpenAlex 匹配质量和宿主 agent 的联网能力。最终投稿前仍建议人工复核期刊官网、最新 JCR、2025 中科院分区、2026 新锐分区、Clarivate Master Journal List 收录状态、版面费、投稿范围、文章类型和撤稿/预警风险。特别注意：不要使用“中科院2026分区”这种表述；2026 年 6 月 17 日发布的是 JCR 2026 release 中的 2025 JIF/JCR 数据，字段应写作 `jif_2025` / `jcr_quartile_2025`；当前 SCI/SCIE 状态也不能只依赖第三方缓存。缓存条目即便带有来源名称，只要 ISSN、IF、SCI 类型或 `2026新锐` 等核心字段为空，也不能当作完整结果复用。

## Attribution and Redistribution

This project is the original sci-select skill by keros68:

https://github.com/keros68/sci-select

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

sci-select is a portable AI agent skill for journal lookup and journal selection. It can query public metrics for known journal names, or turn a manuscript title, abstract, keywords, manuscript excerpt, full text, or research direction into an evidence-backed list of SCI/SCIE/ESCI/SSCI candidate journals.

It helps an agent profile the paper topic, search candidate journals, aggregate an optional user-provided local/static journal index, public LetPub, OpenAlex, and optional XinRui API metrics, rank candidates by scope fit and risk, and produce a compact decision report with ambitious, solid, safer, and cautious submission bands. Reports distinguish `2025 CAS` and `2026 XinRui` partition fields, and treat current Web of Science coverage as something to verify against Clarivate Master Journal List.

It can also prepare optional manual links and copy-ready query text for official publisher Journal Finder tools such as Elsevier, Springer Nature, Wiley, and Taylor & Francis. These checks are manual cross-checks, not default ranking sources.

It does not predict acceptance probability, replace the journal website or author guidelines, automate publisher logins, bypass access restrictions, or treat abstract-only screening as a full manuscript quality assessment.

Workflow:

```text
Title / abstract / keywords / manuscript excerpt
  ↓
Identify research object, research problem, method terms, and fine-grained topic evidence
  ↓
Retrieve candidate journals from public LetPub search
  ↓
Aggregate optional local index, LetPub, OpenAlex, and optional XinRui API metrics
  ↓
Rerank by scope evidence, topic fit, risk, and metrics
  ↓
Produce ambitious, solid, safer, and cautious submission bands
```

Official Journal Finder tools are not run by default. They enter the workflow only when the user asks for them, or when the default candidate list has low recall confidence. In that case, sci-select prepares manual publisher links and copy-ready title, abstract, and keywords text. The user runs those checks in a browser and can send the official results back for comparison.

Quick start:

```text
Install this skill from GitHub and use it for SCI journal selection and candidate journal comparison:
https://github.com/keros68/sci-select
```

After installation, restart or open a new agent window and call:

```text
Use $sci-select to recommend suitable journals for this paper abstract, including ambitious, solid, safer, and cautious options.
```

Direct Python usage:

```bash
pip install -r requirements.txt
```

```python
from scripts.select_journals import select_journals, format_selection_report

bundle = select_journals(
    text=paper_text,
    impact_low="3",
    # xinrui_partition="1区",
    max_candidates=8,
)
print(format_selection_report(bundle["profile"], bundle["results"]))
```

Typical outputs include known-journal metric summaries, topic categories, matched terms, a decision matrix, recommendation tiers, submission bands, fit reasons, risk notes, and source availability notes.

Optional official Finder helper:

```python
from scripts.official_finders import build_finder_checklist, format_finder_checklist

checklist = build_finder_checklist(title=title, abstract=abstract, keywords=keywords)
print(format_finder_checklist(checklist))
```

## License

MIT. See [LICENSE](LICENSE).
