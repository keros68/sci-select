---
name: sci-select
description: "Use when a user wants SCI/SCIE/ESCI/SSCI journal submission help: evidence-backed candidate-journal discovery from a title, abstract, keywords, or manuscript text, direct lookup of a known journal's public metrics and risk flags, or a pre-submission compliance review of a manuscript draft against a chosen target journal's Author Guidelines and same-journal conventions. Also for Chinese requests such as 选刊、投稿期刊推荐、期刊查询、中科院分区、投稿前检查、期刊要求核对. This skill does not assess manuscript quality, predict acceptance, identify a uniquely best journal, draft prose, or simulate peer review."
---

# sci-select

sci-select is a journal lookup and candidate-discovery assistant. It can query known journal names for public metrics, or turn manuscript content into a short, evidence-backed list of journals worth manual review, with fit reasons, core metrics, and risk notes.

## Mode Routing

- User wants to find journals or look up journal metrics -> follow the default workflow below.
- User has a chosen target journal plus a manuscript draft and wants to check compliance or fit against that journal -> read `references/presubmission-review.md` and follow its process (Quick Check is the default scope).
- User wants both -> run discovery first; enter pre-submission review only after the user picks a target journal.

## Default Behavior

Core positioning: sci-select is a candidate-journal discovery, public-metrics aggregation, and submission-risk flagging tool. It is not a best-journal predictor or manuscript-quality reviewer.

Do not evaluate manuscript quality. sci-select estimates journal-scope fit and gathers public journal metrics; it does not judge novelty, experimental strength, data quality, figure quality, writing maturity, peer-review readiness, acceptance probability, or the uniquely best venue. Default output must not label journals as `冲刺`, `主投`, `稳妥`, `保守`, or `保底`.

Use the public-metrics workflow first. It is the stable path.

Official publisher Journal Finder tools are optional cross-checks, not default data sources. Only use them when the user asks to compare with official finders or wants a manual second pass. Do not automate publisher logins, save account state, bypass CAPTCHA or access controls, or make official Finder results part of the default ranking score.

Build the structured manuscript fingerprint before searching (mandatory when an abstract or longer text is available). Read `references/paper-profile.schema.json` for every field's meaning and constraints; extract only claims supported by the supplied text. Use `infer_paper_profile(text)` only as a deterministic fallback; prefer the AI-built fingerprint and pass it as `paper_profile`.

For Chinese manuscripts, keep the human-facing summary in Chinese if useful, but include English or bilingual `primary_field`, `specialty`, `research_object`, `target_audience`, `scope_terms`, and `search_queries` so they can be compared with English journal titles and aims-and-scope pages. If profile terms and scope text use different scripts, report the automatic scope result as unresolved rather than incompatible.

When two independent model calls are available, generate profiles without sharing one model's output with the other, then call `compare_profiles([profile_a, profile_b])` or pass them as `independent_profiles`. If agreement is medium or low, keep multiple query variants, broaden recall, and report the disagreement. Do not force a false consensus and do not add discipline-specific hard-coded rules to reconcile the models.

## Workflow

1. **Build the paper profile.** Build the manuscript fingerprint as described above. Done when: the profile satisfies `references/paper-profile.schema.json`'s required fields, or `infer_paper_profile(text)` was used as a documented fallback.

2. **OpenAlex similar-work recall.** Run the recent-paper neighborhood search using the profile's `search_queries`, and rank literature evidence by similar-paper density relative to the journal's recent publication volume, not raw result count. Done when: OpenAlex Works results are gathered, or the missing-evidence reason (no API key, request failure) is recorded.

3. **Local specialist-title recall.** Run the separate specialist-title channel from the local index, independent of the OpenAlex channel. Done when: the specialist-channel candidate set is produced alongside the OpenAlex set.

   ```python
   from scripts.select_journals import select_journals, format_selection_report

   bundle = select_journals(text=paper_text, paper_profile=profile, impact_low="3")
   print(format_selection_report(bundle["profile"], bundle["results"]))
   ```

   `select_journals` runs steps 2-4 together. For a fully populated `paper_profile` example, see `examples/demo-report.md`.

4. **SQLite / online source metrics aggregation.** Use the bundled SQLite index for title-based partition and Nature Index fields; use online sources for IF, JCR, and current coverage when candidates need them. Query LetPub categories only when recall is too small or the user explicitly supplies categories; use LetPub detail pages for missing IF/coverage fields and direct single-journal queries. Done when: `bundle["results"]` carries metrics with explicit missing-data flags instead of inferred values.

5. **Scope verification and rerank for the top 3-5 candidates.** For a final shortlist, verify the official scope of the leading three to five candidates when access is available.

   ```python
   from scripts.scope_evidence import verify_official_scope
   from scripts.select_journals import rerank_with_scope_evidence

   scope_record = verify_official_scope(
       bundle["profile"], "JOURNAL NAME", official_scope_text, official_scope_url,
       publisher_domain_confirmed=True,
   )
   reranked = rerank_with_scope_evidence(bundle["profile"], bundle["results"], [scope_record])
   ```

   Confirm that the URL domain belongs to the journal or its publisher before setting `publisher_domain_confirmed=True`. Do not label an aggregator, personal page, Journal Finder suggestion, search snippet, or memory-derived description as official scope evidence. If the official text cannot be legally and stably obtained, leave it `待核验`. Done when: `bundle['scope_verification']` is non-empty, or the missing-evidence reason is recorded and the candidate status stays provisional.

6. **Generate the report.** Use `format_selection_report` / `format_selection_matrix` and include every field from "Required Output" below. Done when: the report states candidate status, fit confidence, journal level, evidence, metrics, risk notes, and data notes for each candidate.

### Evidence order and ranking rules

Default evidence order:
1. Recent similar papers actually published by the journal.
2. Official aims and scope plus accepted article type.
3. Fine-grained topic and audience match.
4. Broad category match.
5. Journal metrics such as partition and IF.

Do not include a journal solely because its name, broad category, IF, or partition looks suitable.

## Optional: Official Publisher Finder Checklist

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

## Direct Journal Lookup

For a direct journal lookup, use the metrics helper:

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Journal of Hydrology")
print(format_metrics_line(metrics))
```

## Data Sources

| Source | Purpose | Priority |
|---|---|---|
| Bundled SQLite (`assets/sci_select_journals.sqlite`) | `2025中科院`, `2026新锐`, Nature Index tags | Default, works out of the box |
| User override SQLite (`SCI_SELECT_JOURNAL_INDEX_DB`) | Refreshed/expanded partition and metric fields | Checked before the bundled index |
| Local/static JSON (`SCI_SELECT_JOURNAL_INDEX_PATH`/`_URL`) | Lightweight fallback index | Checked before live sources |
| OpenAlex (Works + metrics) | Similar-paper recall/density, h-index, 2yr citedness, OA, APC | Primary literature-neighborhood and metrics source; needs `OPENALEX_API_KEY` |
| LetPub | IF, `2025中科院`, public `2026新锐`, SCI type, review speed, warnings | Fallback for recall gaps and missing detail fields |
| XinRui WebAPI | `2026新锐` plus on-hold/delist/under-review flags | Optional fallback, needs `XINRUI_API_KEY` |

Full fallback rules, field coverage, and disclaimers: `references/data-sources.md`.

Build or refresh the local index:
```bash
python -m scripts.build_journal_index --cas-2025-xlsx /path/to/cas_2025.xlsx --sqlite-output /path/to/sci_select_journals.sqlite
```
Full flag reference, the ShowJCR import path, and current-source rules: `references/data-sources.md`.

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
- Official-scope status: `已核验`, `已读取待判断`, or `待核验`; include the official source URL whenever text was read.
- Metrics: IF, `2025中科院`, `2026新锐`, SCI type, review speed, h-index/OA/APC if available.
- Risk notes: warning list, ESCI-only status, weak topic fit, scope mismatch, and missing source data.
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
| `validate_profile(profile)` / `compare_profiles(profiles)` | Enforce the model-neutral profile protocol and report cross-model disagreement. |
| `rank_metric_records(profile, records)` | Rank already-fetched metric dictionaries without network access. |
| `verify_official_scope(profile, name, text, url, publisher_domain_confirmed=True)` | Validate supplied official scope evidence after explicit publisher-domain confirmation. |
| `rerank_with_scope_evidence(profile, records, scope_records)` | Rerank the same candidate pool after official-scope checks. |
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
- Do not let high IF, JCR quartile, CAS partition, or XinRui level outrank missing scope evidence, decide candidate scope status, or be the reason a journal is prioritized; keep fit/risk evidence and objective journal level separate.
- Do not call any journal a guaranteed fallback; journal level and acceptance probability are different concepts.
- Do not let one highly cited but weakly related paper dominate similar-work recall; prefer repeated precedents across multiple queries.
- Do not cache or present partial OpenAlex failures as complete multi-source aggregation, and do not reuse a cache entry that has source names but lacks ISSN, IF, SCI type, or `2026新锐`; refresh it instead.
- Do not treat OpenAlex `2yr_mean_citedness` as Journal Impact Factor.
- Do not return only elite journals. Preserve scope-supported high, middle, and regular journal levels without claiming that any level is suitable for the manuscript or safe for acceptance.
- Do not treat historical CAS partition data as a 2026 CAS partition.
- Do not present stale SCI/SCIE labels as current WoS coverage when a journal is on hold, removed, or otherwise abnormal.

More pitfalls: `references/common-mistakes.md`.

## Verification

Run the local behavior tests after changes:

```bash
python -m unittest discover -s tests -v
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite --sample-size 20 --max-severe-mismatch-rate 0.02
```

For benchmark design, held-out evaluation, expert labels, and release-ready metrics, read `references/benchmarking.md`. Never use the original publication venue as the only correct label, and never publish accuracy claims while expert-label readiness is false.
