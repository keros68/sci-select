# sci-select

AI agent 用的 SCI/SCIE/ESCI/SSCI 期刊查询和候选期刊发现 skill。它可以根据期刊名查询公开指标，也可以根据题名、摘要、关键词或正文片段生成一组值得人工复核的候选期刊，并给出方向证据、期刊层级、风险和数据来源说明。

> **项目定位：sci-select 是候选期刊发现、公开指标聚合和投稿风险提示工具，不是“最优期刊预测器”，也不是稿件水平评审器。**
>
> 它回答“哪些期刊值得进一步核验、依据是什么、还有什么风险”，不回答“这篇稿件一定该投哪本、能否录用”。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)

## 它能做什么

- 论文投稿前，根据摘要或全文片段初筛候选期刊。
- 查询单个期刊的 IF、JCR Q 区、中科院分区、新锐分区、Nature Index、SCI 类型、OA/APC、h-index 和审稿速度。
- 分开输出方向匹配、期刊客观层级、证据强弱和待核验项。
- 标出候选期刊的范围匹配、数据缺失、预警、ESCI、WoS 异常和弱匹配风险。
- 选定目标期刊后，按该刊 Author Guidelines 和同刊惯例做投稿前定向审查（原独立项目 [journal-fit](https://github.com/keros68/journal-fit) 已并入本仓库，见 `references/presubmission-review.md`；可选配置 `TAVILY_API_KEY` 提升指南获取成功率）。

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
2. 生成 2–3 组精确检索式，从 OpenAlex 查找近年相似论文；按“相似论文数 / 该刊近年总发文量”计算密度，减少综合大刊因发文量大而占满候选的偏差。
3. 同时从本地索引按论文对象和受众召回专业刊。它是独立召回通道，不依赖大刊黑名单。
4. 用内置 SQLite 匹配 `2025中科院`、`2026新锐` 和 Nature Index；IF、JCR 与收录状态由在线源补充，候选不足时再回退 LetPub 检索。
5. 第一阶段按近期发表先例、细分主题和文章类型形成候选；第二阶段为前 5 本建立官网 scope 核验队列，补入官网证据后对同一候选池重排。
6. 无法合法、稳定取得官网 scope 时明确标为待核验，保留人工 Journal Finder / 官网检查，不伪装成已验证。

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

[OpenAlex 当前 API 说明](https://developers.openalex.org/)要求使用 API key。需要启用“相似论文邻域”召回和 OpenAlex 指标时设置免费 key；未设置时会明确降级到本地专业刊召回与 LetPub，而不是把失败当成无相似论文：

```bash
export OPENALEX_API_KEY="your-key"
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

bundle = select_journals(text=paper_text, paper_profile=profile, impact_low="3")
print(format_selection_report(bundle["profile"], bundle["results"]))
```

完整调用示例（含完整 `paper_profile` 字段）见 [`examples/demo-report.md`](examples/demo-report.md)。

论文画像遵循 [`references/paper-profile.schema.json`](references/paper-profile.schema.json) 的模型无关协议。高风险场景可让两个模型独立生成画像，通过 `independent_profiles=[profile_a, profile_b]` 传入；若方向分歧较大，程序保留多组检索式、扩大召回，并在报告中提示分歧，不强行合成一个“共识方向”。

第一阶段会返回 `bundle["scope_verification"]`。取得前 3–5 本期刊的官网 aims and scope 正文与 URL 后，再做第二阶段核验和重排：

```python
from scripts.scope_evidence import verify_official_scope
from scripts.select_journals import rerank_with_scope_evidence

scope_record = verify_official_scope(
    bundle["profile"],
    "Journal Name",
    official_scope_text,
    "https://publisher.example/journal/aims-and-scope",
    publisher_domain_confirmed=True,
)
reranked = rerank_with_scope_evidence(
    bundle["profile"], bundle["results"], [scope_record]
)
```

这里只接受带官网 URL 的 scope 正文，调用者还必须显式确认该域名属于期刊或出版社。聚合站、个人页面和搜索摘要不能标成“官网已核验”；程序也不会自动登录、绕过验证码或批量抓取出版社网站。

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
python -m scripts.build_journal_index --cas-2025-xlsx "/path/to/cas_2025.xlsx" --sqlite-output "/path/to/sci_select_journals.sqlite"
```

完整参数（XinRui、JCR、Nature Index、ShowJCR 导入路径）见 [`references/data-sources.md`](references/data-sources.md)。

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
可选：两个模型独立画像，检查方向一致性
  ↓
OpenAlex 相似论文密度召回 + 本地专业刊召回
  ↓
SQLite 补充分区；缺失时再回退 LetPub
  ↓
形成初始候选，为前 5 本建立官网 scope 核验队列
  ↓
补入真实官网证据，对同一候选池重排
  ↓
输出候选状态、方向证据、客观期刊层级、风险和待核验项
```

官方 Journal Finder 不自动参与默认评分。只有用户主动要求，或候选召回置信度较低时，sci-select 才生成 Elsevier、Springer Nature、Wiley、Taylor & Francis 等官方入口，供用户手动核验。

## 负责任评测

仓库提交了 60 篇 DOI 清单，覆盖 20 个主题层，每层 3 篇，60 篇使用不同刊源。正文摘要只在本地物化，按主题分层拆为 40 篇开发集和 20 篇完全留出的测试集；原发表期刊单独封存，只作辅助标签。采样器会排除会议/论文集信号、争议收录状态刊源，并检查摘要、ISSN、参考文献和主题命中，但正式评测前仍须由研究者人工审查语料质量。

评测主指标是社区 Recall@K、专家可接受期刊 Recall@K、nDCG 和综合大刊暴露率。标注池必须合并多系统或冻结版本的候选，并允许专家独立补充期刊，不能只评价当前系统自己召回的名单。候选期刊必须由至少两名研究者独立标注 `适合 / 勉强 / 不适合`，模型不能冒充专家。专家标签未完成时，评分脚本会把结果标为 `ready=false`，不得发布“准确率”。完整命令见 [`references/benchmarking.md`](references/benchmarking.md)。

## 数据发布门槛

每次提交都会运行测试和索引审计。审计检查标准化刊名重复、ISSN 格式与校验位、身份冲突、分区格式和字段来源；数据库包含 ISSN 时还会固定种子抽样对照 Crossref。严重错配率高于 2% 或来源缺失时，CI 失败，不发布数据库更新。当前内置库为避免错误身份关联而不含未经核验的 ISSN，因此当前 CI 的外部 Crossref 抽样显示为“不适用”，实际执行的是全库结构与来源检查。

```bash
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite \
  --sample-size 20 --max-severe-mismatch-rate 0.02
```

## 项目结构

- `SKILL.md` - skill 主说明和触发规则。
- `assets/sci_select_journals.sqlite` - 默认 SQLite 索引。
- `scripts/select_journals.py` - 主题识别、候选检索、排序和报告生成。
- `scripts/similar_works.py` - OpenAlex 近年相似论文检索和发表期刊聚合。
- `scripts/scope_evidence.py` - 官网 scope 二次核验和重排证据。
- `scripts/profile_consistency.py` - 模型无关论文画像校验与跨模型一致性检查。
- `scripts/journal_metrics.py` - 已知期刊查询和指标聚合。
- `scripts/build_journal_index.py` - SQLite/JSON 索引构建器。
- `scripts/audit_journal_index.py` - 数据发布前的身份、来源和抽样审计。
- `scripts/benchmark_dataset.py` / `benchmark_run.py` / `benchmark_score.py` - 盲测数据、执行、专家标注和评分。
- `scripts/official_finders.py` - 官方 Journal Finder 人工核验链接。
- `references/data-sources.md` - 数据源说明。
- `references/benchmarking.md` - 60 篇盲测与专家评测协议。
- `references/paper-profile.schema.json` - 模型无关论文画像 schema。
- `examples/demo-report.md` - 示例报告。
- `tests/` - 行为测试。

## 验证

```bash
python -m unittest discover -s tests -v
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite --sample-size 20 --max-severe-mismatch-rate 0.02
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

The default workflow builds a model-neutral manuscript fingerprint, retrieves recent similar works from OpenAlex, normalizes evidence by each journal's recent publication volume, adds a separate specialist-journal recall channel, and uses the bundled SQLite index for partition data. LetPub is a fallback when recall or live fields are incomplete. The top five candidates enter a second-pass official-scope verification queue. Output separates scope-fit evidence, objective journal level, data gaps, and risks; it does not assign manuscript-relative submission roles.

The repository also includes a 60-paper, 20-stratum blinded benchmark protocol, an expert relevance-labeling protocol, Recall@K/nDCG/generalist-exposure scoring, and a CI release gate for journal-index identity and provenance. Human expert labels are required before any accuracy claim is published.

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

---

**同系列 Agent Skills**：[sci-select](https://github.com/keros68/sci-select)（选刊+投稿前审查） · [academic-reference-matcher](https://github.com/keros68/academic-reference-matcher)（文献引用） · [abstract-fig](https://github.com/keros68/abstract-fig)（图形摘要） · [cugb-doctoral-thesis-format](https://github.com/keros68/cugb-doctoral-thesis-format)（学位论文格式） · [ai-cross](https://github.com/keros68/ai-cross)（多模型交叉验证）｜全览见 [keros68](https://github.com/keros68)
