# Data directory

- `evidence/`: the curated evidence catalog used by the whole application.
  - `<study-id>.json`: one file per Study Library study. Shared fields are
    written once per block (`defaults`), and tables are stored cell by cell as
    printed (for example `"194 ± 11*"`), so each record can be compared with
    the PDF. `evidence_catalog.py` expands them into one validated observation
    each.
  - `external_sources.json`: external supporting evidence (E1-E4), kept
    separate from the Study Library.
  - `duration_evidence.json`: within-library associations and statements about
    mission duration. Context only; never used as equations.
- `references/`: the eight source PDFs and `pdf_accessibility_report.md`.
  The Gopalakrishnan et al. (2010) file is a one-page abstract; no legitimate
  open full text was found, so its values are abstract-level ranges.
- `study_library.sqlite3`: local database (ignored by Git) with the study
  summaries.

Evidence is added only through the catalog in `evidence/`; the application has
no way to enter or edit values. To add or correct a value: read it from the
rendered PDF page (the text layer loses minus and ± signs), edit the study file
with page, table, exact wording, statistic, dispersion, n and what n counts,
set `value_type` and `verification_status`, add a pinned test, then run
`python build_evidence_matrix.py` and `python -m pytest`. Calculated and
approximated values need a `formula`; approximations also need notes saying
what was assumed and what would replace it. The loader rejects any record
without provenance or a value type. Do not convert fibre counts into crew
counts or infer individual values from group statistics.

Older databases may still contain a `measurements` table (version 1) and a
`manual_observations` table (Evidence Engine v2). Both are left untouched and
are no longer read.
