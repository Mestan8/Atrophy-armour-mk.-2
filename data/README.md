# Data directory

The Study Library creates its local SQLite database here as
`study_library.sqlite3`. The database is ignored by Git and is initialized from
the source-grounded study summaries in `study_library.py`. On application
startup, `scenario_evidence.py` idempotently adds the scenario's curated,
source-verified publication values to the existing `measurements` table.
The additive database migration also stores source availability, extraction
status, and quantitative verification status separately for each study.

For Gopalakrishnan et al. (2010), only a one-page abstract is available. On
startup, its explicitly reported abstract values are stored with page 1,
abstract section, source wording, and caveats. They are retained as context
only and are not part of the curated scenario catalog or prediction engine.

No other article table values are automatically imported. Any manually entered
measurement must retain its source page, exact wording or context, units,
timepoint, and verification status. Verify values against the rendered source
PDF before marking them `source_verified`. Engine inputs are limited to values
explicitly included in the curated scenario catalog; a verified library record
is not automatically used as an engine input. Do not treat test fixtures as
research evidence.
