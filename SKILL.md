---
name: sci-select
description: Use when a user wants SCI, SCIE, ESCI, SSCI, or journal submission help, including paper-to-journal recommendations from a title, abstract, keywords, manuscript text, or research direction, and direct journal lookup for metrics such as IF, CAS partition, SCI type, review speed, OA/APC, h-index, and data-source notes.
---

# sci-select

sci-select is a journal lookup and paper-to-journal selection assistant. It can query known journal names for public metrics, or turn manuscript content into a short, evidence-backed list of candidate journals with fit reasons, core metrics, and risk notes.

## Default Behavior

Use the public-metrics workflow first. It is the stable path.

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    impact_low="3",
    max_candidates=10,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

For a direct journal lookup, use the metrics helper:

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Journal of Hydrology")
print(format_metrics_line(metrics))
```

Default sources:
- LetPub: impact factor, CAS partition, SCI/SCIE/ESCI type, review speed, warning status.
- OpenAlex: h-index, 2-year mean citedness, OA status, APC when available.

If a source fails, say so in the report. Do not imply h-index, OA, APC, or warning status were checked when the field is missing.

## Required Output

For each recommendation, include:
- Tier: `推荐`, `备选`, `谨慎`, or `不推荐`.
- Submission band: `冲刺`, `稳妥`, `保底`, or `谨慎`.
- Fit reason: why the paper matches the journal scope.
- Metrics: IF, partition, SCI type, review speed, h-index/OA/APC if available.
- Risk notes: warning list, ESCI-only status, weak topic fit, low partition, missing source data.
- Data notes: which source was unavailable, if any.

If the user only provides title/abstract/keywords and no full manuscript quality assessment, do not present only high-IF journals. Provide a submission gradient with ambitious, solid, and safer options, and state that these are journal-selection bands rather than acceptance predictions.

If the user asks about one or more known journals, do not force a recommendation workflow. Query the journal metrics directly and summarize the available IF, partition, SCI type, review speed, OA/APC, h-index, warning status, and missing data notes.

## Quick API

| Function | Purpose |
|---|---|
| `infer_paper_profile(text)` | Infer topics, methods, and LetPub categories from Chinese or English paper text. |
| `select_journals(text, ...)` | Run search, metrics aggregation, ranking, and report preparation. |
| `rank_metric_records(profile, records)` | Rank already-fetched metric dictionaries without network access. |
| `format_selection_report(profile, results)` | Produce the user-facing report. |
| `format_selection_matrix(profile, results)` | Produce a compact Markdown decision table. |
| `assign_submission_bands(results)` | Mark candidates as `冲刺`, `稳妥`, `保底`, or `谨慎`. |
| `get_journal_metrics(name)` | Query public LetPub and OpenAlex metrics for a known journal name. |
| `format_metrics_line(metrics)` | Format one journal's metrics as a compact line. |

Backward compatibility:
- `scripts.recommend.recommend(...)` still works, but new code should call `scripts.select_journals.select_journals(...)`.

## Common Mistakes

- Do not collapse a manuscript into a generic broad field when stronger title, abstract, keyword, or method signals support a more specific journal category.
- Do not cache or present partial OpenAlex failures as complete multi-source aggregation.
- Do not recommend a journal only because IF is high; topic fit is the first filter.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.
- Do not give only elite journals when manuscript quality has not been evaluated. Always preserve a realistic submission gradient.

## Verification

Run the local behavior tests after changes:

```bash
python -m unittest discover -s tests -v
```
