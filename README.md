# sci-select

sci-select is a journal selection assistant for manuscript submission. Give it a title, abstract, keywords, manuscript text, or research direction; it recommends suitable SCI/SCIE/ESCI/SSCI journals and explains the evidence behind each recommendation.

## What It Does

```text
Paper content
  -> topic and method profiling
  -> LetPub category search
  -> LetPub + OpenAlex metric aggregation
  -> fit/risk scoring + submission bands
  -> recommendation report
```

sci-select uses public journal metadata and bibliometric signals.

| Source | Metrics |
|---|---|
| LetPub | IF, CAS partition, SCI/SCIE/ESCI type, review speed, warning status |
| OpenAlex | h-index, 2-year mean citedness, OA status, APC, works/citation counts |

## Quick Start

Install dependencies:

```bash
pip install requests beautifulsoup4
```

Run a recommendation:

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """
Groundwater nitrate source identification using stable isotopes and
hydrochemistry in an agricultural watershed.
"""

bundle = select_journals(
    text=paper_text,
    impact_low="3",
    max_candidates=8,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```

## Main API

| Module | Function | Purpose |
|---|---|---|
| `scripts.select_journals` | `infer_paper_profile(text)` | Infer topics, methods, and LetPub categories |
| `scripts.select_journals` | `select_journals(text, ...)` | Full live recommendation workflow |
| `scripts.select_journals` | `rank_metric_records(profile, records)` | Rank existing metric records without network |
| `scripts.select_journals` | `format_selection_report(profile, results)` | User-facing report |
| `scripts.select_journals` | `format_selection_matrix(profile, results)` | Compact Markdown decision table |
| `scripts.select_journals` | `assign_submission_bands(results)` | Mark candidates as 冲刺/稳妥/保底/谨慎 |
| `scripts.journal_metrics` | `get_journal_metrics(name)` | LetPub + OpenAlex metrics for one journal |
| `scripts.letpub_client` | `advanced_search(...)`, `lookup_journal(...)` | Minimal LetPub public-data client |
| `scripts.recommend` | `recommend(...)` | Backward-compatible wrapper |

## Directory Layout

```text
sci-select/
├── SKILL.md
├── README.md
├── assets/
│   └── journal_cache.json    # generated, not committed
├── scripts/
│   ├── select_journals.py    # sci-select main entry
│   ├── letpub_client.py      # minimal LetPub public-data client
│   ├── journal_metrics.py    # LetPub + OpenAlex aggregation
│   └── recommend.py          # old API wrapper
├── references/
│   └── data-sources.md
├── examples/
│   └── demo-report.md
└── tests/
```

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile scripts/*.py
```

On Windows PowerShell, use:

```powershell
Get-ChildItem scripts -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## Notes

- Recommendations are decision support, not a substitute for checking the journal website and author guidelines.
- If only an abstract is provided, sci-select reports submission bands, not acceptance likelihood. Keep ambitious, solid, and safer choices.
- Topic fit is weighted before impact factor. A high-IF journal with weak scope fit should not outrank a more suitable journal.
- OpenAlex failures are reported as missing source data; they are not silently treated as complete aggregation.

## License

MIT License. See [LICENSE](LICENSE).
