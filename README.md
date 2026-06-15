# sci-select

AI agent 论文投稿选刊 skill：根据题名、摘要、关键词、全文片段或研究方向，推荐 SCI/SCIE/ESCI/SSCI 候选期刊，并输出可复查的期刊指标、匹配理由、风险提示和投稿梯度。

> 中文为主，English version below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

## 适用场景

- 论文写完后，根据摘要、关键词或全文片段初筛投稿期刊。
- 想同时看到冲刺、稳妥、保底和谨慎选择，而不是只列高影响因子期刊。
- 需要把候选期刊的 IF、中科院分区、SCI 类型、OA/APC、h-index、审稿速度等信息放在一个报告里。
- 想让 AI agent 先做期刊范围匹配、指标聚合和风险标注，再由作者人工复核。

## 它做什么

- 从论文内容中识别主题、方法和候选 LetPub 学科分类。
- 使用公开 LetPub 信息检索期刊候选，并补充 IF、中科院分区、SCI/SCIE/ESCI 标签、审稿速度和预警线索。
- 使用 OpenAlex 聚合 h-index、2-year mean citedness、OA 状态、APC、作品量和引用量等补充指标。
- 按主题匹配优先于影响因子的原则，对候选期刊打分和分级。
- 输出 `推荐`、`备选`、`谨慎`、`不推荐`，并进一步标记 `冲刺`、`稳妥`、`保底`、`谨慎` 投稿梯度。
- 在数据源失败或缺失时明示 `OpenAlex未获取`、`LetPub详情未获取` 等数据说明。

## 不做什么

- 不预测录用概率，不承诺命中高影响力期刊。
- 不替代作者阅读官网 scope、author guidelines、版面费政策和最新收录状态。
- 不把只基于摘要的初筛包装成全文质量评价。
- 不绕过验证码、付费墙、机构权限或账号限制。
- 不抓取需要账号访问的论坛内容；投稿体验类信息建议用户自行登录相关平台查看。

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
pip install requests beautifulsoup4
```

运行一个公开指标选刊流程：

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    impact_low="3",
    max_candidates=8,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

如果已经有本地指标记录，也可以跳过联网检索，只用排序和报告格式化逻辑：

```python
from scripts.select_journals import infer_paper_profile, rank_metric_records, format_selection_report

profile = infer_paper_profile(paper_text)
ranked = rank_metric_records(profile, records)

print(format_selection_report(profile, ranked))
```

## 输出内容

常见输出包括：

- 识别方向和命中主题；
- 快速决策表；
- 候选期刊的推荐等级和投稿梯度；
- IF、中科院分区、SCI 类型、审稿速度、h-index、OA/APC 等指标；
- 主题匹配理由；
- 预警、ESCI、综述型期刊、弱匹配、数据缺失等风险说明；
- 数据来源缺失或失败提示。

示例报告见 [`examples/demo-report.md`](examples/demo-report.md)。

## 文件结构

- `SKILL.md` - skill 主说明和触发规则。
- `scripts/select_journals.py` - 主题识别、候选检索、排序和报告生成主入口。
- `scripts/journal_metrics.py` - LetPub + OpenAlex 指标聚合。
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

选刊质量取决于输入文本完整度、公开网页可访问性、LetPub 页面结构、OpenAlex 匹配质量和宿主 agent 的联网能力。最终投稿前仍建议人工复核期刊官网、最新 JCR/中科院分区、收录状态、版面费、投稿范围、文章类型和撤稿/预警风险。

## Attribution and Redistribution

This project is the original sci-select skill by keros68:

https://github.com/keros68/sci-select

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

sci-select is a portable AI agent skill for journal selection. It turns a manuscript title, abstract, keywords, manuscript excerpt, full text, or research direction into an evidence-backed list of SCI/SCIE/ESCI/SSCI candidate journals.

It helps an agent profile the paper topic, search candidate journals, aggregate public LetPub and OpenAlex metrics, rank candidates by scope fit and risk, and produce a compact decision report with ambitious, solid, safer, and cautious submission bands.

It does not predict acceptance probability, replace the journal website or author guidelines, bypass access restrictions, or treat abstract-only screening as a full manuscript quality assessment.

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
pip install requests beautifulsoup4
```

```python
from scripts.select_journals import select_journals, format_selection_report

bundle = select_journals(text=paper_text, impact_low="3", max_candidates=8)
print(format_selection_report(bundle["profile"], bundle["results"]))
```

Typical outputs include topic categories, matched terms, a decision matrix, journal metrics, recommendation tiers, submission bands, fit reasons, risk notes, and source availability notes.

## License

MIT. See [LICENSE](LICENSE).
