# sci-select Data Sources

sci-select uses public journal metadata by default.

## LetPub

Used for journal search, impact factor, 2025 CAS partition, SCI/SCIE/ESCI labels, review-speed text, and warning-list hints.

CAS partition note: the official CAS journal partition site states that from 2026 the Chinese Academy of Sciences Documentation and Information Center no longer updates or releases the journal partition table. Report this field as `2025中科院`. Do not report "2026 CAS partition".

SCI/SCIE coverage note: LetPub labels can lag behind Web of Science changes. Treat them as useful hints, not the final authority for current coverage.

## OpenAlex

Used for source-level bibliometric context: h-index, 2-year mean citedness, OA status, APC, works count, and citation count.

If OpenAlex fails or has no matching source, sci-select reports `OpenAlex未获取` instead of filling in unknown values.

OpenAlex does not replace JCR or Clarivate Master Journal List for current SCI/SCIE/SSCI/ESCI coverage.

## XinRui WebAPI

Used for 2026 XinRui partition and status flags when `XINRUI_API_KEY` is configured. The API requires `Authorization: Bearer ApiKey`, supports year 2026, and returns journal `researcharea`, `jcrcategory`, `onHold`, `delist`, and `underReview` fields.

If XinRui is unavailable, sci-select still shows the `2026新锐` column and marks it as `未获取`.

## Clarivate Master Journal List / JCR

Use Clarivate Master Journal List or JCR as the authority for current Web of Science coverage. If current coverage is not checked, mark it as `收录需复核`.

Known status override: `Science of the Total Environment` is treated as `WoS已移除/不推荐` because it has reported Web of Science/SCIE removal. Stale third-party data should not override that warning.
