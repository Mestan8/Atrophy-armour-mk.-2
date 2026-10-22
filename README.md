# Atrophy Armour

Atrophy Armour is an educational tool for organizing published evidence about
muscle changes associated with long-duration spaceflight. The Scenario Explorer
shows selected observations and transparent calculations. It does not predict
in-flight atrophy, astronaut performance, or individual outcomes.

## Using the Scenario Explorer

The Study Library retains all eight sources, but the Scenario Explorer only
offers combinations backed by complete curated numerical records:

- **English et al. (2015):** the 12 knee, ankle, and trunk isokinetic torque or
  total-work outcomes; all-participant observations at their reported R+5,
  R+14, or R+30 timepoints (trunk begins at R+14); men, women, iRED-era, and
  ARED-era subgroup observations at R+5 for knee/ankle and R+14 for trunk.
- **Fitts et al. (2010):** soleus slow type I fibre diameter or peak isometric
  fibre force, comparing L-55 ± 2 days preflight with landing day (R+0).
  Fibre-level measurements are not whole-joint strength, and fibre counts are
  not participant counts.

Choose a supported study, outcome, comparison, and available timepoint. Results
update when a selection changes. When an English comparison has multiple
verified postflight points, an additional recovery-series view is available.
Select any plotted point to open its observation-specific details, including
the value, biological measurement level, timepoint, source PDF/page/table,
sample-size definition, and recorded uncertainty or limitations. Point IDs
are linked to verified Study Library records; changing the scenario clears
the prior selection. Click an empty part of the chart to clear a point
selection before selecting it again after closing its details.

The mission-duration slider is intentionally absent from the explorer:
duration is not used to scale observations or predict change during flight.
The existing duration validation and context helpers remain in the analysis
engine for compatibility; published values and calculations are unchanged.

## Phase 5 study coverage and model limits

The Study Library contains the two original engine-supported studies and six
additional sources. All six files are present in `data/references/`; the local
Gopalakrishnan et al. (2010) document is a one-page abstract, not the complete
article.

| Study | Local source | Availability and current quantitative use |
|---|---|---|
| Scott et al. (2023) | `Effects of exercise countermeasures on multisystem function in long duration spaceflight astronauts (2023).pdf` | Full text available; text accessible, but new values are not verified for engine use. |
| Trappe et al. (2009) | `Exercise in space human skeletal muscle after 6 months aboardthe International Space Station (2009.pdf` | Full text available; text accessible, but new values are not verified for engine use. |
| English et al. (2020), NASA Sprint Study | `High intensity training during spaceflight results from the NASA Sprint Study (2020).pdf` | Full text available; text accessible, but new values are not verified for engine use. |
| LeBlanc et al. (2000) | `Muscle volume, MRI relaxation times (T2), and bodycomposition after spaceﬂight (2000).pdf` | Full text available; text accessible; shuttle/Mir cohorts remain distinct from ISS evidence. |
| Gopalakrishnan et al. (2010) | `Muscle volume, strength, endurance, and exercise loads during 6-month missions in space (2010) PDF.pdf` | **Abstract only**; abstract-reported values are source-checked and stored as context, not calculation inputs. |
| Greene et al. (2021) | `Trunk Skeletal Muscle Changes on CT with Long-Duration (2021).pdf` | Full text available; text accessible, but new values are not verified for engine use. |

Source availability, extraction status, and quantitative verification status
are stored separately in the Study Library and shown in the interface. The
five Gopalakrishnan abstract measurements retain page, abstract section, exact
source wording, and the abstract-only limitation. Its broad regional and
joint-level ranges do not identify enough compatible endpoint detail for a
specific calculation; in particular, the abstract's calf-volume range
(`-10 to 16%`) is flagged as ambiguous. Its values therefore do not calibrate,
validate, or drive predictions. No missing full-text methods, tables, figures,
or results have been reconstructed.

The additional full-text papers are registered with their bibliographic
metadata and extraction state. Their tables have not been manually
source-verified for this integration, so their values are not promoted into
verified measurements or used in calculations. The engine continues to use
only the curated, source-verified English et al. (2015) and Fitts et al. (2010)
observations. This is intentional: the additional studies cover incompatible
biological levels, populations, outcomes, and timepoints, and the available
evidence does not support a defensible common fitted model.

## Evidence audit

The two engine-supported studies measure different outcomes at different
biological levels. Their numerical values are kept separate.

### English et al. (2015)

- **Population:** 37 analyzed flight datasets from 29 men and 8 women on ISS
  Expeditions 1-25. Three crew members contributed two flights, counted as
  separate datasets. The study reports 37 analyzed observations from 39 eligible
  crew members.
- **Outcomes:** whole-joint isokinetic peak torque for knee, ankle, and trunk
  movements; total work for selected 180-degree/s knee tests. These are not
  direct muscle-fibre measurements.
- **Exposures/comparisons:** sex and primary resistance-exercise hardware
  (iRED on Expeditions 1-17; ARED on Expeditions 18-25). The authors also report
  correlations between preflight knee-extension strength and subsequent
  strength change. The hardware comparison is retrospective and confounded with
  expedition era; it is not a randomized countermeasure trial.
- **Timepoints:** L-180 and L-60 preflight tests, with L-60 as the comparison
  baseline; postflight tests at R+5, R+14, and R+30. Trunk testing began after
  flight at R+14. Sample sizes vary by outcome and timepoint (typically 25-37
  in Table III; subgroup values are smaller).
- **Mission duration:** Table I reports group means +/- SD: all participants
  163 +/- 38 days; men using iRED 164 +/- 41; men using ARED 161 +/- 38; women
  using iRED 185 +/- 13; women using ARED 142 +/- 37. These are group summaries,
  not individual mission durations or observed minima/maxima.
- **Numerical evidence:** Table III reports mean percent change from L-60 and
  95% CIs by outcome and postflight timepoint. For example, knee extension at
  60 degrees/s was -11.0% (n=37; reported 95% CI -7.2 to -14.8) at R+5.
  Table IV reports sex-stratified means/CIs, and Table V reports iRED/ARED
  means/CIs and tests of group interaction. The displayed means and CIs are
  group-level summaries, not individual records (PDF pages 4-5; journal pages
  A71-A72). Table I duration summaries are on PDF page 2 (journal page A69).
  The paper's figures also show medians, interquartile ranges, and outliers.
- **Associations and limitations:** Pearson correlations for knee extension at
  60 degrees/s were r=-0.47 for absolute preflight strength vs. absolute change
  and r=-0.54 for relative values. These are associations, not prediction
  equations or causal effects. The study did not measure strength change during
  flight; some postflight values are missing; trunk is first tested after
  landing; and ARED loading was not routinely measured. The paper reports no
  significant sex or hardware interaction.

### Fitts et al. (2010)

- **Population:** ten ISS crew members participated; damaged postflight biopsy
  samples from one were excluded, leaving nine analyzed. The ten participants
  included five US astronauts and five Russian cosmonauts.
- **Outcomes:** soleus and gastrocnemius slow type I and fast type II fibre
  diameter, cross-sectional area, peak isometric force, shortening velocity,
  peak power, and other contractile/structural properties. These are fibre- and
  biopsy-level outcomes, not whole-joint torque.
- **Exposures/comparisons:** slow/type I vs. fast/type II fibres, soleus vs.
  gastrocnemius, and descriptive treadmill/exercise exposure. Table 1 reports
  group weekly exercise summaries (including treadmill time 146 +/- 32 min/week,
  range 64-312, and speed 3.2 +/- 0.5 mph, range 2.1-5.5). These are not
  matched participant-level predictors in this application.
- **Timepoints and mission duration:** biopsy at L-55 +/- 2 days and on landing
  day (R+0), about 6-8 hours after landing. The analyzed crew's flight duration
  was 177 +/- 4 days, range 161-192 days. R+0 is a postflight biopsy timepoint,
  not an in-flight measurement.
- **Numerical evidence:** the abstract reports soleus type I fibre diameter
  values of 98 to 79 micrometres (authors describe this as 20% atrophy) and
  peak force of 0.86 to 0.56 mN (authors report a 35% decline). Tables 2 and 3
  report the all-crew soleus type I means with SEM: diameter 98 +/- 1 um
  (n=540 fibres) preflight and 79 +/- 1 um (n=458) postflight; peak force
  0.86 +/- 0.01 mN (n=540) and 0.56 +/- 0.01 mN (n=458). The paper reports
  SEMs and fibre counts; these fibres are subsamples from nine crew members,
  not independent crew observations. Tables also provide individual crew-level
  summaries, but not raw independent fibre/participant records. Table 1 is on
  PDF page 3; Tables 2 and 3 are on PDF pages 6 and 7 (journal pages 3569 and
  3572-3573).
- **Associations and limitations:** the abstract reports that percentage
  diameter decrease was associated with initial fibre size (r=0.87) and
  inversely associated with treadmill running (r=0.68). These associations are
  not regression equations or causal effects. The cohort is small, biopsies may
  not represent whole-muscle change, and a group-level fibre result must not be
  generalized to whole-joint strength.

## Scenario Explorer

The Scenario Explorer has five scientific inputs plus a mission-duration
slider. The analysis-view selector changes how observations are displayed; it
is not an additional scientific model input:

1. **Study** — all eight studies can be selected individually. English et al.
   and Fitts et al. have numerical scenario controls; the six additional
   studies show their evidence and model-eligibility status without an
   unsupported numerical output. The combined view keeps the two supported
   studies in separate panels with independent controls; their results are
   never pooled.
2. **Muscle or joint region** — knee, ankle, or trunk for English et al.;
   soleus or gastrocnemius for Fitts et al. These are the anatomical targets
   actually tested in each paper.
3. **Measured outcome** — movement-specific isokinetic torque/work or a
   fibre property such as diameter or peak force. Units and available results
   depend on the selected study.
4. **Comparison group** — overall cohort, sex, or exercise-device era for
   English et al.; fibre type for Fitts et al. Subgroup results are descriptive
   and do not establish causal effects.
5. **Measurement timepoint** — English et al. offers postflight R+5, R+14, and
   R+30 where reported; Fitts et al. uses L-55 +/- 2 days to landing day R+0.
   Recovery timepoints remain separate from mission duration.
6. **Mission-duration slider** — 90-240 days, default 177 days, step 1 day.
   It remains explicitly context-only: no compatible linked observations
   support an outcome-versus-duration relationship. The range is
   rounded from approximately two SD around the English all-cohort duration
   (163 +/- 38 days); 177 days is the Fitts cohort mean. A warning is shown
   outside the English subgroup mean +/- one-SD envelope (105-205 days) or the
   Fitts observed range (161-192 days), as applicable. The English envelope is
   not an individual min/max. Duration is contextual only and never multiplies
   an observed change or generates a loss curve.

Baseline strength and weekly treadmill exposure are not additional controls:
the reported strength/exposure associations do not provide a verified,
compatible individual-level dataset for a scenario calculation. English et al.
report correlations, and Fitts et al.'s exercise summaries and fibre outcomes
cannot be linked as independent participant-level predictors here.

The analysis-view selector offers an observed-data comparison and an English
et al. postflight-recovery view. The recovery chart uses days after return on
its horizontal axis and shows discrete verified observations with their
reported 95% CIs; it does not draw a continuous trajectory. Other views show
the reported English group mean and CI, or Fitts
et al. preflight and landing-day fibre group means. The Fitts chart does not
add uncertainty bars because the published fibre counts do not provide
uncertainty for the paired change.

Changing mission duration updates the displayed context and evidence-range
warning, but does not alter source measurements. The available studies do not
provide linked, independent outcome observations across enough mission
durations to support a duration-versus-outcome fit or a continuous in-flight
prediction. The app therefore does not estimate a hypothetical duration's
physiological effect.

### Analysis mode and calculations

- **English et al.:** the engine retrieves the paper's reported mean percent
  change and 95% CI for the selected outcome, group, and timepoint. It displays
  those values as published relative to L-60; it does not fit a new model.
  Negative percent change means a lower postflight group mean. Sex and hardware
  group comparisons are accompanied by the paper's non-significance and
  observational-design cautions.
- **Fitts et al.:** for the all-crew soleus type I diameter and peak-force
  means (Tables 2-3), the engine calculates
  `absolute change = postflight - preflight` and
  `percent change = (postflight - preflight) / preflight * 100`. This gives
  -19 micrometres and -19.4% for diameter, and -0.30 mN and -34.9% for peak
  force. These ratios are calculated from reported group mean levels and are
  not the mean of participant-level percent changes. The abstract's rounded
  descriptions are 20% and 35%, respectively. The app displays the SEM and
  fibre counts for each pre/post group mean but does not invent a confidence
  interval or uncertainty for the derived change.
- Other Fitts selections are explicitly marked as lacking a matching,
  source-verified numerical record. Their source tables include individual
  crew/fibre data that need careful curation before further calculations.
- No validated, externally validated, or duration-dependent prediction model
  is implemented. The English paper's correlations are not used as equations;
  the Fitts paper's reported associations are not treated as causal.

### Provenance and data integrity

The existing SQLite database is preserved and migrated additively with
study-level source-availability, extraction, and quantitative-verification
fields. On app startup, seeding remains idempotent. Source-checked values from
English et al. Tables III-V and Fitts et al. Tables 2-3 retain their units,
timepoints, sample sizes when stated, source page/table, source wording, and
verification status. The five Gopalakrishnan abstract measurements retain
their abstract page, section, and exact wording; their study-level status is
`context_only`. Existing measurement records are not replaced. The engine uses
only records matching the original studies' curated source catalog, so even a
source-verified abstract transcription is not automatically a model input.
Unverified or altered records are excluded from quantitative results.

To add further values, use the Measurements tab. Keep the source PDF page,
table/figure, unit, measurement timepoint, baseline, exact source wording,
sample size and its meaning, and uncertainty/extraction notes. New entries
remain `unverified` until checked against the rendered PDF. Marking a record
verified does not automatically make it an engine input; add the measurement
to the curated scenario catalog only after its biological level, units,
population, and analysis are reviewed and tests are added. Do not convert
fibre counts into crew sample sizes or infer individual values from group
means/SDs.

## Setup

Python 3.14 is the target environment. From the project root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If a dependency does not yet provide a compatible Python 3.14 release or wheel
for the platform, use a compatible release when available; an installation
failure is not validation of the scientific code.

## Run the app

```powershell
python -m streamlit run app.py
```

## Diagnose reference PDFs

```powershell
python inspect_references.py
```

The diagnostic checks embedded text, page coverage, and a preview. It does not
validate table structure or numerical accuracy and does not perform OCR. The
source PDFs are preserved in `data/references/`.

## Run tests

```powershell
python -m pytest
```

Tests cover published values, percent-change arithmetic and signs, units,
confidence intervals, input validation, missing/unverified records, study-level
separation, duration boundaries/warnings, and the existing Study Library.

## Project structure

- `app.py` — Streamlit Scenario Explorer and Study Library interface.
- `scenario_inputs.py` — typed scenario inputs, available controls, and
  study-specific validation.
- `model.py` — scientific calculations, duration warnings, and interpretation.
- `scenario_evidence.py` — source-checked observations, provenance, and
  idempotent Study Library seeding/retrieval, including verified recovery data.
- `plotting.py` — verified relative-change, recovery, and fibre comparison
  charts.
- `study_library.py` — SQLite schema, study summaries, and measurement
  verification rules.
- `database.py` — SQLite connection helper.
- `data/` — local Study Library database and source PDFs.
- `tests/` — application helper, Study Library, and scenario-engine tests.

This is an educational research tool, not a clinical, operational, or
mission-planning system.
