# sci-select Data Sources

sci-select uses public journal metadata by default.

## Bundled SQLite Journal Index

sci-select ships with `assets/sci_select_journals.sqlite` so it works immediately after download. The bundled database uses sci-select's own SQLite schema and normalized title keys. It is not the ShowJCR project database. The current bundled database includes 2025 CAS partition fields, 2026 XinRui partition fields, and 2026 Nature Index publication flags.

The bundled index intentionally omits unverified ISSN/eISSN, JIF/JCR quartile, and SCI/SCIE/SSCI/ESCI fields. A cross-source audit found that shifted ISSNs in one imported table could cause JCR metrics to be attached to a different journal. Live sources or a user-verified override index now provide those fields; missing data must remain missing rather than being inferred.

Nature Index source note: the 2026 publication-venue list is imported from the official Nature Index FAQ. The current official list contains 178 venues, described as 177 journals and 1 conference proceeding after the June 2026 expansion.

Runtime lookup order:

```text
SCI_SELECT_JOURNAL_INDEX_DB
  ↓
SCI_SELECT_JOURNAL_INDEX_PATH / SCI_SELECT_JOURNAL_INDEX_URL
  ↓
assets/sci_select_journals.sqlite
  ↓
live public sources
```

## Optional User SQLite Journal Index

Users can configure `SCI_SELECT_JOURNAL_INDEX_DB` to load a user-generated `sci_select_journals.sqlite` before the bundled database. This is useful when refreshing the bundled data or adding future JCR/CAS/XinRui fields.

Build a SQLite index from local files:

```bash
python -m scripts.build_journal_index \
  --cas-2025-xlsx /path/to/cas_2025.xlsx \
  --xinrui-2026-xlsx /path/to/xinrui_2026.xlsx \
  --jcr-file /path/to/jcr_2025.xlsx \
  --nature-index-url https://www.nature.com/nature-index/faq \
  --sqlite-output /path/to/sci_select_journals.sqlite
```

ShowJCR can be used as a user-supplied input database or public CSV source, but sci-select does not vendor ShowJCR code, raw CSV files, or `jcr.db`:

```bash
python -m scripts.build_journal_index \
  --showjcr-db /path/to/jcr.db \
  --sqlite-output /path/to/sci_select_journals.sqlite
```

The SQLite schema stores normalized lookup keys plus each journal row as JSON payload. User-provided indexes can use ISSN/eISSN first, but an ISSN hit is accepted only when the requested and stored journal titles are compatible; otherwise lookup falls back to normalized title.

## Optional Local / Static JSON Journal Index

Users can configure `SCI_SELECT_JOURNAL_INDEX_PATH` or `SCI_SELECT_JOURNAL_INDEX_URL` to load a local or self-hosted `journals.json` / `search_index.json` file before live public lookups. JSON remains supported for lightweight deployments.

Supported JSON shapes:

```json
{"meta": {"source": "local"}, "journals": [{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491"}]}
```

```json
[{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491"}]
```

Recognized row fields include `title`, `issn`, `eissn`, `jif_2025`, `jcr_release_year`, `jcr_data_year`, `jcr_quartile_2025`, `if_2023`, `if_year`, `jcr_quartile`, `cas_2025`, `xuankan_2026`, `nature_index`, `nature_index_year`, `nature_index_articles`, `nature_index_publication_type`, `warning_latest`, `xuankan_warning`, and `tags`.

This source is intended for stable local partition metadata and fast direct journal lookup. If it conflicts with LetPub on `2025中科院` or `2026新锐`, sci-select keeps the local/static index value and adds a `分区来源冲突需复核` note.

Do not bundle ShowJCR source code, ShowJCR `jcr.db`, raw Excel workbooks, temporary generated JSON indexes, or cache files. The repository-bundled database should remain a sci-select generated SQLite file using sci-select's own schema.

## LetPub

Used for journal search, impact factor, 2025 CAS partition, public 2026 XinRui partition shown on the journal page, SCI/SCIE/ESCI labels, review-speed text, and warning-list hints.

The current advanced-search table labels its partition column `新锐期刊分区表`. The parser stores that column only as `xinrui_partition_2026`; it does not reuse the ambiguous legacy `partition` field. The journal detail page remains the preferred source when available.

LetPub is a fallback in paper-selection mode. OpenAlex Works supplies candidate journals and ISSNs when available; the bundled SQLite supplies title-based partition fields. LetPub category recall is used when the literature neighborhood is too small, and detail pages fill missing IF/coverage fields. Direct single-journal lookup also uses LetPub for public details such as review-speed text.

CAS partition note: the official CAS journal partition site states that from 2026 the Chinese Academy of Sciences Documentation and Information Center no longer updates or releases the journal partition table. Report this field as `2025中科院`. Do not report "2026 CAS partition".

SCI/SCIE coverage note: LetPub labels can lag behind Web of Science changes. Treat them as useful hints, not the final authority for current coverage.

## OpenAlex

Used for source-level bibliometric context: h-index, 2-year mean citedness, OA status, APC, works count, and citation count.

The Works search endpoint is also used for cross-disciplinary candidate recall. sci-select runs two or three compact searches built from the manuscript object, problem, contribution, and context; it then aggregates recent journal articles by source. Repeated publication precedents across multiple queries are stronger evidence than one highly cited result. See the official [OpenAlex search guide](https://developers.openalex.org/guides/searching) and [Works API](https://developers.openalex.org/api-reference/works/list-works).

[OpenAlex's current API overview](https://developers.openalex.org/) requires an API key for access; `OPENALEX_MAILTO` remains optional contact metadata. Without a key, sci-select skips the live OpenAlex request, uses the local specialist-title channel plus LetPub fallback, and reports the missing literature-neighborhood evidence explicitly.

If OpenAlex fails or has no matching source, sci-select reports `OpenAlex未获取` instead of filling in unknown values.

OpenAlex does not replace JCR or Clarivate Master Journal List for current SCI/SCIE/SSCI/ESCI coverage.

## XinRui WebAPI

Optional fallback for 2026 XinRui partition and status flags when `XINRUI_API_KEY` is configured. The API requires `Authorization: Bearer ApiKey`, supports year 2026, and returns journal `researcharea`, `jcrcategory`, `onHold`, `delist`, and `underReview` fields.

Use LetPub's public page first. If neither LetPub nor the optional API returns XinRui data, sci-select still shows the `2026新锐` column and marks it as `未获取`.

## Clarivate Master Journal List / JCR

Use Clarivate Master Journal List or JCR as the authority for current Web of Science coverage. If current coverage is not checked, mark it as `收录需复核`.

JCR terminology note: the June 17, 2026 JCR release contains 2025 JIF/JCR data. Use fields such as `jif_2025`, `jcr_quartile_2025`, `jcr_release_year=2026`, and `jcr_data_year=2025`.

Known status override: `Science of the Total Environment` is treated as `WoS已移除/不推荐` because it has reported Web of Science/SCIE removal. Stale third-party data should not override that warning.
