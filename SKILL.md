---
name: sci-select
description: Use when a user provides a paper title, abstract, keywords, manuscript text, or research direction and wants suitable SCI, SCIE, ESCI, SSCI, or journal submission recommendations.
---

# sci-select

sci-select is a paper-to-journal selection assistant. It turns manuscript content into a short, evidence-backed list of candidate journals with fit reasons, core metrics, and risk notes.

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

## Quick API

| Function | Purpose |
|---|---|
| `infer_paper_profile(text)` | Infer topics, methods, and LetPub categories from Chinese or English paper text. |
| `select_journals(text, ...)` | Run search, metrics aggregation, ranking, and report preparation. |
| `rank_metric_records(profile, records)` | Rank already-fetched metric dictionaries without network access. |
| `format_selection_report(profile, results)` | Produce the user-facing report. |
| `format_selection_matrix(profile, results)` | Produce a compact Markdown decision table. |
| `assign_submission_bands(results)` | Mark candidates as `冲刺`, `稳妥`, `保底`, or `谨慎`. |

Backward compatibility:
- `scripts.recommend.recommend(...)` still works, but new code should call `scripts.select_journals.select_journals(...)`.

## Common Mistakes

- Do not default English abstracts to generic environmental science when stronger terms are present. `groundwater`, `stable isotope`, and `hydrochemistry` should map to water resources and geochemistry.
- Do not cache or present partial OpenAlex failures as complete multi-source aggregation.
- Do not recommend a journal only because IF is high; topic fit is the first filter.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.
- Do not give only elite journals when manuscript quality has not been evaluated. Always preserve a realistic submission gradient.

## Verification

Run the local behavior tests after changes:

```bash
python -m unittest discover -s tests -v
```
