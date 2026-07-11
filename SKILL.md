---
name: sci-select
description: Use when a user wants SCI, SCIE, ESCI, SSCI, or journal submission help, including evidence-backed candidate-journal discovery from a title, abstract, keywords, manuscript text, or research direction, and direct journal lookup for metrics such as IF, latest available CAS partition or 2026+ XinRui partition, SCI type, review speed, OA/APC, h-index, risks, and data-source notes. This skill does not assess manuscript quality, predict acceptance, or identify a uniquely best journal.
---

# sci-select

sci-select is a journal lookup and candidate-discovery assistant. It can query known journal names for public metrics, or turn manuscript content into a short, evidence-backed list of journals worth manual review, with fit reasons, core metrics, and risk notes.

## Default Behavior

Core positioning: sci-select is a candidate-journal discovery, public-metrics aggregation, and submission-risk flagging tool. It is not a best-journal predictor or manuscript-quality reviewer.

Do not evaluate manuscript quality. sci-select estimates journal-scope fit and gathers public journal metrics; it does not judge novelty, experimental strength, data quality, figure quality, writing maturity, peer-review readiness, acceptance probability, or the uniquely best venue. Default output must not label journals as `冲刺`, `主投`, `稳妥`, `保守`, or `保底`.

Use the public-metrics workflow first. It is the stable path.

Official publisher Journal Finder tools are optional cross-checks, not default data sources. Only use them when the user asks to compare with official finders or wants a manual second pass. Do not automate publisher logins, save account state, bypass CAPTCHA or access controls, or make official Finder results part of the default ranking score.

For paper-to-journal candidate discovery, build a structured manuscript fingerprint before searching. This is mandatory when an abstract or longer text is available. Extract only claims supported by the supplied text:
- `direction_summary`: one sentence stating the primary field, specialty, and the role of methods.
- `title`: the manuscript title, used to exclude the target paper itself from similar-work evidence when testing published papers.
- `research_object` and `research_question`: what is studied and what problem is answered.
- `contribution_type`: applied finding, method development, dataset/resource, review, clinical study, theory, or another explicit type.
- `target_audience`: the research community likely to review and use the result.
- `methods`: tools and methods; do not promote them to the primary field unless the contribution is methodological.
- `exclusions`: plausible but wrong journal communities that should not drive recall.
- `search_queries`: two or three discriminative queries combining object + problem + contribution, not a copied full abstract.

Use `infer_paper_profile(text)` only as a deterministic fallback. Prefer the AI-built fingerprint and pass it as `paper_profile`.

Default evidence order:
1. Recent similar papers actually published by the journal.
2. Official aims and scope plus accepted article type.
3. Fine-grained topic and audience match.
4. Broad category match.
5. Journal metrics such as partition and IF.

Do not include a journal solely because its name, broad category, IF, or partition looks suitable. Run the recent-paper neighborhood search by default. For a final shortlist, verify the official scope of the leading candidates when access is available. If recent-paper retrieval or official-page verification is unavailable, state the missing evidence and keep the candidate status provisional.

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    paper_profile={
        "direction_summary": "groundwater nitrate reference conditions; hydrochemistry is the analytical framework",
        "primary_field": "hydrogeology",
        "specialty": "groundwater nitrate reference conditions",
        "research_object": "shallow aquifer nitrate states",
        "research_question": "how status separation changes reference estimation",
        "contribution_type": "applied methodological framework",
        "target_audience": ["hydrogeologists", "groundwater-quality researchers"],
        "methods": ["hydrochemistry", "bootstrap uncertainty"],
        "exclusions": ["general analytical chemistry", "machine-learning methods"],
        "search_queries": [
            "groundwater nitrate reference condition aquifer hydrochemistry",
            "nitrate baseline status separation redox groundwater",
        ],
    },
    # Optional: strict current XinRui filter, e.g. "1区".
    # xinrui_partition="1区",
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
- Bundled sci-select journal index SQLite: `assets/sci_select_journals.sqlite`, used automatically so the skill works immediately after download. It is keyed by normalized journal title and provides `2025中科院`, `2026新锐`, `nature_index`, and related tags. It intentionally excludes unverified bundled ISSN/JIF/JCR/coverage fields.
- Optional user override SQLite: `SCI_SELECT_JOURNAL_INDEX_DB`, used before the bundled index when a user wants to refresh or replace the bundled data with their own generated `sci_select_journals.sqlite`.
- Optional local/static journal index JSON: user-provided `journals.json` or `search_index.json` configured with `SCI_SELECT_JOURNAL_INDEX_PATH` or `SCI_SELECT_JOURNAL_INDEX_URL`. This is a lightweight fallback when SQLite is not used.
- LetPub: impact factor, 2025 CAS partition, public 2026 XinRui partition shown on the journal page, SCI/SCIE/ESCI type, review speed, warning status.
- OpenAlex: h-index, 2-year mean citedness, OA status, APC when available.
- OpenAlex Works: recent similar-paper retrieval, publication precedents, topic labels, and candidate-journal recall. Use `OPENALEX_API_KEY` when configured; transient failure must fall back with an explicit warning.
- XinRui WebAPI: optional fallback for 2026 XinRui partition and on-hold/delist/under-review flags when `XINRUI_API_KEY` is configured.

In paper-selection mode, prefer OpenAlex Works for candidate recall and pass its journal ISSN into metric lookup when available. Use the bundled SQLite index for title-based partition and Nature Index fields. Query LetPub categories only when the literature neighborhood is too small or the user explicitly supplies LetPub categories; use LetPub detail pages for missing IF/coverage fields and direct single-journal queries.

If a source fails, say so in the report. Do not imply h-index, OA, APC, or warning status were checked when the field is missing.
If a local/static journal index and LetPub disagree on `2025中科院` or `2026新锐`, keep the local/static index value and add a `分区来源冲突需复核` data note.
The bundled index is a sci-select generated database, not a vendored ShowJCR project database. Do not bundle ShowJCR source code, ShowJCR `jcr.db`, raw Excel workbooks, generated caches, or unrelated third-party files.

Local index builder:
```bash
python -m scripts.build_journal_index \
  --cas-2025-xlsx /path/to/cas_2025.xlsx \
  --xinrui-2026-xlsx /path/to/xinrui_2026.xlsx \
  --jcr-file /path/to/jcr_2025.xlsx \
  --nature-index-url https://www.nature.com/nature-index/faq \
  --sqlite-output /path/to/sci_select_journals.sqlite
```
ShowJCR can be used only as a user-supplied input database or public CSV source:
```bash
python -m scripts.build_journal_index \
  --showjcr-db /path/to/jcr.db \
  --sqlite-output /path/to/sci_select_journals.sqlite
```

Current-source rules:
- Do not write "2026 中科院分区". The official CAS journal partition site states that the Chinese Academy of Sciences Documentation and Information Center stopped updating and releasing the journal partition table from 2026. Output CAS data as `2025中科院`.
- For 2026 and later Chinese partition-style evaluation, output XinRui data as `2026新锐`. Prefer LetPub's public journal page when it shows XinRui partition. Use `XINRUI_API_KEY` only as an optional fallback. If neither source provides it, still include the field and write `未获取` or `需复核`.
- If the user asks for "新锐1区", call `select_journals(..., xinrui_partition="1区")` and exclude records whose fetched `2026新锐` field does not match. Do not rely on the legacy `partition` argument for this strict current-source filter.
- LetPub and OpenAlex are not authoritative for current Web of Science coverage. For current SCI/SCIE/SSCI/ESCI inclusion, prioritize Clarivate Master Journal List or JCR. If the current status was not checked, write `收录需复核`.
- Nature Index is a selective publication-venue flag, not a replacement for IF, JCR quartile, CAS partition, XinRui partition, or scope fit. Output it as `NI=2026` when available.
- Known current exception: `Science of the Total Environment` has reported Web of Science/SCIE removal. Do not present it as normal SCIE based only on stale LetPub, cached, or third-party data; mark it as `WoS已移除/不推荐` and ask the user to verify in Clarivate Master Journal List before any submission decision.

## Required Output

For each candidate, include:
- Candidate status: `优先核验`, `可选`, `谨慎`, or `排除`. Internal APIs may retain the legacy tier values `推荐`, `备选`, `谨慎`, and `不推荐` for compatibility.
- Fit confidence: `强`, `中`, or `弱`, based on publication precedents, official scope, and fine-grained topic evidence.
- Journal level: `高位`, `中位`, `常规`, or `待定`, based primarily on current partition/JCR evidence rather than global IF cutoffs.
- Fit reason: why the paper matches the journal scope.
- Recent precedents: up to three similar papers and publication years when available.
- Official-scope status: `已核验` or `待核验`.
- Metrics: IF, `2025中科院`, `2026新锐`, SCI type, review speed, h-index/OA/APC if available.
- Risk notes: warning list, ESCI-only status, weak topic fit, low partition, missing source data.
- Data notes: which source was unavailable, if any.

If the user only provides title/abstract/keywords, infer topic, audience, article type, and search terms only. Do not infer hidden experimental quality. Report high/middle/regular as journal-level metadata, never as manuscript suitability or acceptance safety.

If the user asks "is this paper good enough for this journal?", answer that sci-select cannot decide manuscript quality. Offer only scope/metric fit and list what would need a separate manuscript review: novelty, methods, evidence strength, figures, writing, and journal-specific recent articles.

If the candidate list has low recall confidence, say so clearly. Low confidence includes candidates whose fit reasons are mostly "主题相关性需要人工复核" or whose fit scores are weak across the list. In that case, do not make the gradient sound authoritative; ask the user to add manual target journals, verify journal scope, or use optional official Journal Finder checks.

If the user asks about one or more known journals, do not force a recommendation workflow. Query the journal metrics directly and summarize the available IF, `2025中科院`, `2026新锐`, SCI type, review speed, OA/APC, h-index, warning status, and missing data notes.

## Quick API

| Function | Purpose |
|---|---|
| `infer_paper_profile(text)` | Infer topics, methods, and LetPub categories from Chinese or English paper text. |
| `merge_paper_profile(fallback, structured)` | Merge an AI-built manuscript fingerprint over deterministic fallback data. |
| `select_journals(text, ...)` | Run similar-paper recall, category search, metrics aggregation, ranking, and report preparation. |
| `rank_metric_records(profile, records)` | Rank already-fetched metric dictionaries without network access. |
| `format_selection_report(profile, results)` | Produce the user-facing report. |
| `format_selection_matrix(profile, results)` | Produce a compact Markdown decision table. |
| `assign_candidate_labels(results)` | Add objective journal levels and candidate labels without judging manuscript quality. |
| `assign_submission_bands(results, profile=...)` | Backward-compatible alias for `assign_candidate_labels`. |
| `build_finder_checklist(title, abstract, keywords)` | Prepare optional manual official Journal Finder links and copy-ready query text. |
| `format_finder_checklist(checklist)` | Format the optional manual Finder checklist. |
| `get_journal_metrics(name, source_mode=..., issn=...)` | Query one journal; pass a known ISSN when available, use `selection` for recommendation or `full` for LetPub details. |
| `format_metrics_line(metrics)` | Format one journal's metrics as a compact line. |

Backward compatibility:
- `scripts.recommend.recommend(...)` still works, but new code should call `scripts.select_journals.select_journals(...)`.

## Common Mistakes

- Do not collapse a manuscript into a generic broad field when stronger title, abstract, keyword, or method signals support a more specific journal category.
- Do not treat method terms such as machine learning, deep learning, social media data, GIS, remote sensing, modeling, or statistics as the primary journal field unless the manuscript's contribution is mainly methodological.
- Do not let high IF or partition outrank missing scope evidence without warning.
- Do not equate `1区/2区/3区` with `冲刺/主投/稳妥/保底`; default output reports objective journal levels only.
- Do not call any journal a guaranteed fallback; journal level and acceptance probability are different concepts.
- Do not let one highly cited but weakly related paper dominate similar-work recall; prefer repeated precedents across multiple queries.
- Do not cache or present partial OpenAlex failures as complete multi-source aggregation.
- Do not reuse a cache entry that has source names but lacks ISSN, IF, SCI type, or `2026新锐`; refresh it instead.
- Do not silently treat a third-party static index as authoritative when it conflicts with LetPub, JCR, Clarivate, or known status overrides.
- Do not merge two records by ISSN alone when their normalized journal titles are incompatible. Prefer an exact title match and reject mismatched identity data.
- Do not describe the bundled sci-select SQLite as copied from ShowJCR. ShowJCR can be one possible local import source, but runtime uses sci-select's own schema.
- Do not commit raw Excel source files, ShowJCR `jcr.db`, ShowJCR source code, temporary generated JSON indexes, or cache files into the repository.
- Do not prioritize a journal only because IF is high; topic fit is the first filter.
- Do not treat publisher Journal Finder suggestions as neutral quality judgments; use them only as optional manual cross-checks.
- Do not add automated login, account-state reuse, CAPTCHA bypass, or publisher-site scraping to the default workflow.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.
- Do not return only elite journals. Preserve scope-supported high, middle, and regular journal levels without claiming that any level is suitable for the manuscript or safe for acceptance.
- Do not treat historical CAS partition data as a 2026 CAS partition.
- Do not present stale SCI/SCIE labels as current WoS coverage when a journal is on hold, removed, or otherwise abnormal.

## Verification

Run the local behavior tests after changes:

```bash
python -m unittest discover -s tests -v
```
