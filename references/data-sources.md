# sci-select Data Sources

sci-select uses public journal metadata by default.

## LetPub

Used for journal search, impact factor, CAS partition, SCI/SCIE/ESCI labels, review-speed text, and warning-list hints.

## OpenAlex

Used for source-level bibliometric context: h-index, 2-year mean citedness, OA status, APC, works count, and citation count.

If OpenAlex fails or has no matching source, sci-select reports `OpenAlex未获取` instead of filling in unknown values.
