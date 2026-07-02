# sci-select

AI agent 用的 SCI/SCIE/ESCI/SSCI 期刊查询和投稿选刊 skill。它可以根据期刊名查询指标，也可以根据题名、摘要、关键词或正文片段生成候选期刊梯度，并给出主题匹配、分区、风险和数据来源说明。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

## 适合做什么

- 论文投稿前，根据摘要或全文片段初筛候选期刊。
- 查询单个期刊的 IF、JCR Q 区、中科院分区、新锐分区、Nature Index、SCI 类型、OA/APC、h-index 和审稿速度。
- 生成 `冲刺`、`稳妥`、`保底`、`谨慎` 四档投稿建议，而不是只按影响因子排序。
- 标出候选期刊的范围匹配、数据缺失、预警、ESCI、WoS 异常和弱匹配风险。

## 内置数据

下载后即可用。仓库自带 `assets/sci_select_journals.sqlite`，默认包含：

| 字段 | 说明 |
|---|---|
| `jif_2025` / `jcr_quartile_2025` | 2025 JIF 与 JCR Q 区 |
| `cas_2025` | 2025 中科院分区 |
| `xuankan_2026` | 2026 新锐分区 |
| `nature_index` | 2026 Nature Index publication-venue 标记 |
| `issn` / `eissn` | 期刊匹配键 |
| `warning_latest` / `tags` | 预警和补充标签 |

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

仓库不打包原始 Excel、ShowJCR 原始 `jcr.db`、ShowJCR 源码或运行缓存。默认库是 sci-select 自己 schema 生成的 SQLite 文件；原始表格和公开页面只作为构建输入。

## 快速开始

在支持 skills / agent instructions 的工具里安装：

```text
请从 GitHub 安装这个 skill，并在 SCI 期刊查询、论文投稿选刊、候选期刊对比时优先使用它：
https://github.com/keros68/sci-select
```

安装后，新开窗口或重启 agent，然后调用：

```text
使用 $sci-select 根据下面这篇论文摘要推荐投稿期刊，并列出冲刺、稳妥、保底和谨慎选择。
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

根据论文内容推荐期刊：

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
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

Windows PowerShell：

```powershell
$env:SCI_SELECT_JOURNAL_INDEX_DB = "D:\journal-index\sci_select_journals.sqlite"
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
识别研究对象、研究问题、方法词和细分主题证据
  ↓
召回候选期刊并聚合本地索引、LetPub、OpenAlex、新锐 API
  ↓
按 scope 证据、主题契合、风险和指标重排
  ↓
输出冲刺、稳妥、保底、谨慎梯度报告
```

官方 Journal Finder 不自动参与默认评分。只有用户主动要求，或候选召回置信度较低时，sci-select 才生成 Elsevier、Springer Nature、Wiley、Taylor & Francis 等官方入口，供用户手动核验。

## 项目结构

- `SKILL.md` - skill 主说明和触发规则。
- `assets/sci_select_journals.sqlite` - 默认 SQLite 索引。
- `scripts/select_journals.py` - 主题识别、候选检索、排序和报告生成。
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
- 不替代作者阅读期刊官网、scope、author guidelines 和版面费政策。
- 不把摘要初筛包装成全文质量评价。
- 不自动登录出版社网站，不绕过验证码、付费墙、机构权限或账号限制。
- 不把 Nature Index、IF 或分区当作唯一排序标准，主题契合仍是第一过滤条件。
- 当前 SCI/SCIE/SSCI/ESCI 收录状态最终应以 Clarivate Master Journal List 或 JCR 复核。
- 不写“中科院2026分区”。中科院分区字段使用 `2025中科院`，新体系使用 `2026新锐`。

## Attribution and Redistribution

This project is the original sci-select skill by keros68:

https://github.com/keros68/sci-select

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

sci-select is an AI-agent skill for journal lookup and manuscript-to-journal selection. It can query metrics for known journals, or turn a manuscript title, abstract, keywords, excerpt, or research direction into an evidence-backed list of SCI/SCIE/ESCI/SSCI candidate journals.

It ships with a bundled SQLite index for 2025 JIF/JCR quartiles, 2025 CAS partitions, 2026 XinRui partitions, 2026 Nature Index venue flags, ISSN matching, and warning tags. Optional local SQLite or JSON indexes can override the bundled data.

Typical output includes journal metrics, scope-fit reasons, recommendation tiers, submission bands, risk notes, and missing-source notes. sci-select does not predict acceptance, replace journal author guidelines, automate publisher logins, bypass access restrictions, or treat abstract-only screening as a full manuscript quality review.

Quick use:

```text
Use $sci-select to recommend suitable journals for this paper abstract, including ambitious, solid, safer, and cautious options.
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
