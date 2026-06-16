---
name: sci-select
description: Use when a user wants SCI, SCIE, ESCI, SSCI, or journal submission help, including paper-to-journal recommendations from a title, abstract, keywords, manuscript text, or research direction, and direct journal lookup for metrics such as IF, latest available CAS partition or 2026+ XinRui partition, SCI type, review speed, OA/APC, h-index, and data-source notes.
---

# sci-select

sci-select is a journal lookup and paper-to-journal selection assistant. It can query known journal names for public metrics, or turn manuscript content into a short, evidence-backed list of candidate journals with fit reasons, core metrics, and risk notes.

## Default Behavior

Use the public-metrics workflow first. It is the stable path.

Official publisher Journal Finder tools are optional cross-checks, not default data sources. Only use them when the user asks to compare with official finders or wants a manual second pass. Do not automate publisher logins, save account state, bypass CAPTCHA or access controls, or make official Finder results part of the default ranking score.

For paper-to-journal recommendations, do not blindly trust keyword matching. First make a short domain judgment:
- Primary research object or application domain: what is being studied.
- Methods and data sources: how it is studied.
- Fine-grained topic evidence: the concrete problem, object, population, material, process, or task named in the manuscript.
- Likely journal communities: where papers on this object are normally reviewed.

Treat method words such as machine learning, deep learning, social media data, GIS, remote sensing, modeling, or statistics as methods unless the manuscript itself is about the method. If the script-inferred categories overemphasize methods, override `categories` manually when calling `select_journals`.

Use fine-grained topic evidence before impact factor when explaining fit. A lower-IF journal with scope evidence in the title, field, or candidate metadata can outrank a high-IF journal that only matches a broad method or category.

Default decision order:
1. Identify the manuscript's primary object/domain in your own judgment.
2. Use `infer_paper_profile(text)` as a helper, not as the final decision.
3. If inferred categories are mostly method/tool fields while the manuscript is applied, pass AI-judged `categories` into `select_journals`.
4. If the correct LetPub category is uncertain, say so and present the category assumption before running search. Do not silently search only method/tool categories.

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    # Optional: pass AI-judged categories when the topic/method balance is subtle.
    # categories=[{"category1": "环境科学与生态学", "category2": "水资源"}],
    impact_low="3",
    max_candidates=10,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

If the user asks for official publisher Journal Finder checks, provide manual links and copy-ready query text:

```python
from scripts.official_finders import build_finder_checklist, format_finder_checklist

checklist = build_finder_checklist(
    title="PASTE TITLE HERE",
    abstract="PASTE ABSTRACT HERE",
    keywords=["keyword 1", "keyword 2"],
)
print(format_finder_checklist(checklist))
```

For a direct journal lookup, use the metrics helper:

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Journal of Hydrology")
print(format_metrics_line(metrics))
```

Default sources:
- LetPub: impact factor, 2025 CAS partition, public 2026 XinRui partition shown on the journal page, SCI/SCIE/ESCI type, review speed, warning status.
- OpenAlex: h-index, 2-year mean citedness, OA status, APC when available.
- XinRui WebAPI: optional fallback for 2026 XinRui partition and on-hold/delist/under-review flags when `XINRUI_API_KEY` is configured.

If a source fails, say so in the report. Do not imply h-index, OA, APC, or warning status were checked when the field is missing.

Current-source rules:
- Do not write "2026 中科院分区". The official CAS journal partition site states that the Chinese Academy of Sciences Documentation and Information Center stopped updating and releasing the journal partition table from 2026. Output CAS data as `2025中科院`.
- For 2026 and later Chinese partition-style evaluation, output XinRui data as `2026新锐`. Prefer LetPub's public journal page when it shows XinRui partition. Use `XINRUI_API_KEY` only as an optional fallback. If neither source provides it, still include the field and write `未获取` or `需复核`.
- LetPub and OpenAlex are not authoritative for current Web of Science coverage. For current SCI/SCIE/SSCI/ESCI inclusion, prioritize Clarivate Master Journal List or JCR. If the current status was not checked, write `收录需复核`.
- Known current exception: `Science of the Total Environment` has reported Web of Science/SCIE removal. Do not present it as normal SCIE based only on stale LetPub, cached, or third-party data; mark it as `WoS已移除/不推荐` and ask the user to verify in Clarivate Master Journal List before any submission decision.

## Required Output

For each recommendation, include:
- Tier: `推荐`, `备选`, `谨慎`, or `不推荐`.
- Submission band: `冲刺`, `稳妥`, `保底`, or `谨慎`.
- Fit reason: why the paper matches the journal scope.
- Metrics: IF, `2025中科院`, `2026新锐`, SCI type, review speed, h-index/OA/APC if available.
- Risk notes: warning list, ESCI-only status, weak topic fit, low partition, missing source data.
- Data notes: which source was unavailable, if any.

If the user only provides title/abstract/keywords and no full manuscript quality assessment, do not present only high-IF journals. Provide a submission gradient with ambitious, solid, and safer options, and state that these are journal-selection bands rather than acceptance predictions.

If the candidate list has low recall confidence, say so clearly. Low confidence includes candidates whose fit reasons are mostly "主题相关性需要人工复核" or whose fit scores are weak across the list. In that case, do not make the gradient sound authoritative; ask the user to add manual target journals, verify journal scope, or use optional official Journal Finder checks.

If the user asks about one or more known journals, do not force a recommendation workflow. Query the journal metrics directly and summarize the available IF, `2025中科院`, `2026新锐`, SCI type, review speed, OA/APC, h-index, warning status, and missing data notes.

## Quick API

| Function | Purpose |
|---|---|
| `infer_paper_profile(text)` | Infer topics, methods, and LetPub categories from Chinese or English paper text. |
| `select_journals(text, ...)` | Run search, metrics aggregation, ranking, and report preparation. |
| `rank_metric_records(profile, records)` | Rank already-fetched metric dictionaries without network access. |
| `format_selection_report(profile, results)` | Produce the user-facing report. |
| `format_selection_matrix(profile, results)` | Produce a compact Markdown decision table. |
| `assign_submission_bands(results)` | Mark candidates as `冲刺`, `稳妥`, `保底`, or `谨慎`. |
| `build_finder_checklist(title, abstract, keywords)` | Prepare optional manual official Journal Finder links and copy-ready query text. |
| `format_finder_checklist(checklist)` | Format the optional manual Finder checklist. |
| `get_journal_metrics(name)` | Query public LetPub and OpenAlex metrics for a known journal name. |
| `format_metrics_line(metrics)` | Format one journal's metrics as a compact line. |

Backward compatibility:
- `scripts.recommend.recommend(...)` still works, but new code should call `scripts.select_journals.select_journals(...)`.

## Common Mistakes

- Do not collapse a manuscript into a generic broad field when stronger title, abstract, keyword, or method signals support a more specific journal category.
- Do not treat method terms such as machine learning, deep learning, social media data, GIS, remote sensing, modeling, or statistics as the primary journal field unless the manuscript's contribution is mainly methodological.
- Do not let high IF or partition outrank missing scope evidence without warning.
- Do not cache or present partial OpenAlex failures as complete multi-source aggregation.
- Do not recommend a journal only because IF is high; topic fit is the first filter.
- Do not treat publisher Journal Finder suggestions as neutral quality judgments; use them only as optional manual cross-checks.
- Do not add automated login, account-state reuse, CAPTCHA bypass, or publisher-site scraping to the default workflow.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.
- Do not give only elite journals when manuscript quality has not been evaluated. Always preserve a realistic submission gradient.
- Do not treat historical CAS partition data as a 2026 CAS partition.
- Do not present stale SCI/SCIE labels as current WoS coverage when a journal is on hold, removed, or otherwise abnormal.

## Verification

Run the local behavior tests after changes:

```bash
python -m unittest discover -s tests -v
```
