# sci-select

sci-select is a Codex skill and Python toolkit for journal lookup and paper-to-journal selection.

It can query public metrics for a known journal, or turn a manuscript title, abstract, keywords, excerpt, or research direction into an evidence-backed shortlist of SCI/SCIE/ESCI/SSCI candidate journals.

The core workflow is:

```text
manuscript text
-> topic and community judgment
-> public journal search and metric aggregation
-> scope-fit and risk ranking
-> submission bands with data notes
```

## Install

Copy or clone this repository into your Codex skills directory.

Windows PowerShell:

```powershell
git clone https://github.com/keros68/sci-select.git "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS/Linux:

```bash
git clone https://github.com/keros68/sci-select.git ~/.codex/skills/sci-select
```

Then start a new Codex thread and call:

```text
Use $sci-select to recommend suitable journals for this paper abstract, including ambitious, solid, safer, and cautious options.
```

## What It Produces

- Known-journal metric summaries.
- Candidate journal shortlists from paper text.
- Submission bands: ambitious, solid, safer, and cautious.
- Fit reasons tied to topic, object, method, and journal community.
- Public metrics such as IF, 2025 CAS, 2026 XinRui when available, SCI type, review speed, OpenAlex signals, OA/APC notes, and warning flags.
- Risk notes for weak topic fit, missing data, ESCI-only status, abnormal WoS status, and source failures.
- Optional manual Journal Finder checklist links and copy-ready title/abstract/keywords.

## Direct Python Use

Install dependencies:

```bash
pip install -r requirements.txt
```

Query a known journal:

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Journal of Hydrology")
print(format_metrics_line(metrics))
```

Run a journal-selection workflow:

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

Prepare optional manual publisher checks:

```python
from scripts.official_finders import build_finder_checklist, format_finder_checklist

checklist = build_finder_checklist(
    title="PASTE TITLE HERE",
    abstract="PASTE ABSTRACT HERE",
    keywords=["keyword 1", "keyword 2"],
)

print(format_finder_checklist(checklist))
```

## Data Boundaries

sci-select uses public and agent-accessible sources. It does not predict acceptance probability, replace journal websites or author guidelines, automate publisher logins, bypass CAPTCHA, or treat abstract-only screening as a full manuscript quality assessment.

Important source conventions:

- Use `2025 CAS` for the last CAS partition table.
- Use `2026 XinRui` for 2026+ Chinese partition-style data when available.
- Treat current Web of Science coverage as something to verify against Clarivate Master Journal List.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.

## Repository Layout

- `SKILL.md` - Codex skill instructions.
- `agents/openai.yaml` - UI metadata for compatible runtimes.
- `scripts/select_journals.py` - main topic profiling, retrieval, ranking, and report workflow.
- `scripts/journal_metrics.py` - known-journal metric lookup.
- `scripts/official_finders.py` - optional manual Journal Finder checklist builder.
- `scripts/letpub_client.py` - public LetPub lookup helper.
- `references/data-sources.md` - source notes.
- `examples/demo-report.md` - sample report.
- `tests/` - behavior tests.

## Verify

```bash
python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
