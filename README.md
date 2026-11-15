# Atrophy Armour Mk. 2

Atrophy Armour Mk. 2 is an educational tool that organizes published evidence about
skeletal-muscle changes in long-duration spaceflight. It shows published group
results side by side, each traced to a page and table of its source. It is not a
clinical, operational, or mission-planning predictor and does not estimate any
individual's or mission's outcome.

## Evidence model (Evidence Engine v2)

All numbers come from one catalog in `data/evidence/`:

- **Eight study files**, one per Study Library study, holding every extracted
  observation with: study, outcome category, outcome, region and muscle/joint,
  biological level, unit, statistic, value, dispersion type and values, n and
  what n counts (crew, flight datasets or fibres), cohort, subgroup, sex,
  countermeasure/hardware, mission duration with its source wording and page,
  baseline and measurement timepoint, source file, PDF page, table or figure,
  exact source wording or cell, value type, verification status, and notes.
- **`external_sources.json`**: the separate *External supporting evidence*
  register (E1-E4). These sources are not library studies.
- **`duration_evidence.json`**: every within-library link between mission
  duration and outcome (Scott 2023 rank associations, LeBlanc 2000 statements).

`evidence_catalog.py` loads and validates the files and refuses to start if any
record lacks provenance or a value type. Every value is labelled:

| Value type | Meaning |
|---|---|
| `reported` | Copied from the source as printed. |
| `calculated` | Arithmetic on reported values; the formula is shown (for example percent change from pre/post group means). |
| `digitized` | Read off a figure. None are used at present. |
| `approximation` | An assumption, interpolation or fit the source does not prove: every duration-model output, and the Scott 2023 CI midpoints. |

Values were transcribed from rendered PDF pages, not from the text layer, which
drops minus and ± signs in several PDFs. Suspect cells are stored as printed and
flagged in their notes (for example Sprint Table 1's leg lean mass SE of 0.04).
`docs/evidence_matrix.md` summarizes what each study contributes to each
category; regenerate it with `python build_evidence_matrix.py`.

### Coverage

| Study | Catalog contents |
|---|---|
| English et al. (2015) | 82 values: knee/ankle/trunk torque and knee work, mean % change with 95% CI, all/men/women/iRED/ARED, R+5/R+14/R+30 (Tables III-V). |
| Fitts et al. (2010) | 96 values: soleus and gastrocnemius type I and II fibre diameter, CSA, peak force, shortening velocity; all crew and high/low treadmill groups; mean ± SEM; n = fibres (Tables 2-6). |
| Scott et al. (2023) | 31 values: leg CSA, leg/bench press force, power, work, 1RM, body composition, VO2peak at R+1/R+7/R+30 (Fig. 2 printed estimates and 95% CIs). |
| Trappe et al. (2009) | 35 values: calf MRI volumes at R+4/R+19, calf MVC and isokinetic torque at R+7/R+13, peak power, MHC I fibre share (Tables 5-6, text). |
| English et al. (2020), Sprint | 104 values: CON and SPRINT torque, work, 1RM, leg lean/fat mass, VO2peak and related measures; mean ± SE (Tables 1-4). |
| LeBlanc et al. (2000) | 45 values: MRI volumes for 17-day Spacelab and 115-197-day Shuttle/Mir crews, DXA body composition (Tables 1-2, text). Shuttle/Mir, not ISS. |
| Gopalakrishnan et al. (2010) | 7 abstract-level values: printed ranges only. **Abstract only**: no legitimate open full text was found (Europe PMC, Unpaywall and NASA NTRS were checked). The calf range "-10 to 16%" is stored as printed, flagged ambiguous, and not plotted. |
| Greene et al. (2021) | 16 values: trunk CT CSA and attenuation at return, 1 year and 2-4 years; SMI and ASMI at return (Table 1). |

## Using the Scenario Explorer

The Explorer works in two steps, top to bottom:

- **Step 1 · Scenario**: the study filter and five scientific controls. When a
  control changes, the server recalculates which options are valid and greys
  out the rest with the reason, but no results are calculated yet. The
  scenario is saved in the browser and restored on reload.
- **Step 2 · Results**: press **Show results** to see, in order, the result
  rows, the mission-duration slider, the three charts and the explanation
  panels. The slider updates the results and charts live. If a scenario
  control changes afterwards, the results are marked out of date and the
  button becomes **Update results**; nothing is recalculated until it is
  pressed. **Reset scenario to defaults** clears the saved scenario and hides
  the results.

The five scientific controls:

1. **Outcome category**: muscle size, whole-joint strength, endurance/work,
   fibre-level, body composition, aerobic capacity.
2. **Muscle group / region**: thigh/knee, calf/ankle, trunk, whole leg, upper
   body, whole body.
3. **Countermeasure / exercise regimen**: the groups each paper reports (for
   example iRED vs ARED era, CON vs SPRINT, high vs low treadmill, Spacelab vs
   Shuttle/Mir). Differences are descriptive, not causal.
4. **Crew subgroup**: all, men, women. Men and women are available only from
   English 2015 Table IV.
5. **Postflight recovery day**: the reported R+x test days, from landing day to
   2-4 years (Greene 2021). Nothing is interpolated between them.

The **study filter** shows one study or all studies that report the selection;
results are listed separately and never averaged. Options with no data are
greyed out with the reason (for example "Not measured by Greene et al. (2021)").
Every result names its source page and table and opens a full provenance view.

### Mission-duration slider and model

The slider's range and default come from the selected study's reported mission
durations. Moving it changes the model value shown for each result. Every model
output is labelled `approximation`.

- **Muscle size, LeBlanc 2000 regions: multi-cohort model.** Straight segments
  join real cohort means at 8 days (STS-47, quoted by external source E1),
  17 days (Spacelab) and 115-197 days (Shuttle/Mir), held flat across 115-197
  days because LeBlanc report no significant slope with duration there. These
  crews differ in vehicle and exercise, so duration is confounded with
  countermeasure. Dotted parts are interpolation; dashed parts beyond 197 days
  are extrapolation.
- **Everything else: linear fallback.** One group mean at one mission length is
  the only data, so the line runs from zero at launch to that value. A plain
  notice beside the slider and in each chart caption says so. Dashed segments
  and an extrapolation warning mark mission lengths outside the study's reported
  range (min-max where printed, otherwise mean ± 1 SD, labelled as such).
- **No model** for abstract ranges without a mean (Gopalakrishnan 2010).
- **No ground-analogue curve** is drawn. The bed-rest reviews (E2, E3) are cited
  as context only; E3's equation was not read (abstract only).

Scott 2023's rank associations between mission length and change (Somers' D)
are shown next to the matching results as direction-only context, not equations.

### Charts

Three interactive Plotly charts with hover details (value, unit, uncertainty,
n, timepoint, value type, source) and click-through provenance: outcome against
mission duration (model plus real anchor points), recovery over postflight days
(reported points only, not joined), and a cross-study comparison for the
selected category and region.

## 3D Simulator

`simulator.html` shows an interactive 3D model of the human soleus. You can zoom
continuously from the lower leg (L0) through a belly cross-section (L1), a
fascicle (L2) and a single fibre (L3) down to one sarcomere (L4). A mission-day
slider (day 0 to 177, the cohort's mean mission length) moves the model from
preflight to the reported postflight values of the same nine ISS crew members
(Fitts et al. 2010, Trappe et al. 2009). It is a visualization of published
group means, not a prediction for any individual.

- **Values and provenance:** every value is in `data/simulator/soleus_parameters.json`
  (value, unit, dispersion, n and what n counts, value type, source, page/table
  and exact quote). This file is separate from the evidence catalog because it
  allows the extra value type `illustrative` (drawn counts, shapes and
  positions) and holds anatomy/ultrastructure sources that are not Study
  Library studies. `simulator_model.py` validates it at server start and
  evaluates one day: `GET /api/simulator/soleus?day=&cohort=&shape=&phase=`.
- **Timepoints:** fibre and electron-microscopy values are landing-day biopsies
  (R+0); muscle volumes are MRI at R+4, with an R+19 recovery snap. Nothing was
  measured in flight.
- **In-between days** are approximations. The default shape reuses the
  LeBlanc 2000 multi-cohort soleus curve from `duration_model.py`
  (`normalized_shape`), scaled to this cohort's own endpoints. A straight-line
  alternative follows the shape of a 70-day bed-rest study. Thin-filament
  (EM) values are not interpolated, because a 17-day flight changed them in the
  opposite direction.
- **Crew groups:** all crew (n = 9), or Fitts' high (n = 4) and low (n = 5)
  treadmill groups. Group values are never mixed with all-crew values.
- **Rendering:** Three.js 0.186.1 (MIT) is committed under
  `web/assets/vendor/three/`, with no CDN and no build step. Add `?fps=1` to the
  URL to show the frame rate.

## Measurements page

Every study is shown through the same seven category slots (the six above plus
**Recovery**). A slot without data reads "Not measured in this study" (or "Not
reported in the abstract"). Each row gives percent change from the study's own
baseline (reported, or calculated with the formula shown), the original value
and unit, statistic, dispersion, n and what it counts, timepoint and source.
Filters for study, category, region and timepoint; one comparison chart per
category. The page is read-only. Evidence is added only through the curated
catalog in `data/evidence/`, which is schema-validated at startup and pinned by
tests (see `data/README.md`).

## Study Library

The library holds exactly eight studies. The *External supporting evidence*
register (E1 NASA HRP evidence report; E2 Winnard 2019 and E3 Marusic 2021,
bed-rest reviews; E4 Comfort 2021, spaceflight meta-analysis) is listed
separately on the same page with citations, links, quoted text and how each
source was used.

## Known limitations

- No study measured muscle during flight; all outcomes are pre/postflight.
- Only LeBlanc 2000 offers measured groups at more than one mission length,
  and those groups differ in more than duration.
- Linear lines assume an even rate of change. LeBlanc's own data suggest loss
  levels off, and E3 describes a logarithmic pattern in bed rest, so the
  straight line is probably the wrong shape.
- Scott 2023 values are CI midpoints (approximation); per-endpoint means are in
  supplemental tables that are not in the local PDF.
- Greene 2021 gives mission length only as "4-6 months"; its range is
  converted at 30 days per month and marked approximate.
- Studies use different statistics (SD, SE, SEM, 95% CI, ranges); error bars
  show what each source reports and are not comparable as precision.

## Evidence audit

The two studies audited first (English 2015, Fitts 2010) measure different outcomes at different
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
python app.py
```

The app starts a local server at <http://127.0.0.1:8501/> and opens it in your
default browser. Press Ctrl+C to stop it. Use `--port`, `--host` and
`--no-browser` as needed. Everything, including the charting library, is
served locally, including the Inter typeface (self-hosted `.woff2`, with the
system font stack as fallback).

The server is read-only: it answers GET requests and refuses any write with
405 Method Not Allowed.

### Troubleshooting

- **Run without activating the virtual environment:** from the project folder,
  run `.\.venv\Scripts\python.exe app.py`.
- **"Port 8501 is already in use":** another server, usually an older Atrophy Armour
  Mk. 2 still running in a different terminal, holds the port. Close that
  terminal (or press Ctrl+C in it), or find and stop the process with
  `netstat -ano | findstr :8501` and `Stop-Process -Id <PID>`. Alternatively,
  start on another port with `python app.py --port 8502`. The server refuses to
  share a port, so it can no longer start silently next to an old one.
- **"The running server looks out of date" or "Server is outdated" on the
  Explorer page:** the page and the running server come from different
  versions of the code. Stop the server, start it again, and hard-refresh the
  page (Ctrl+F5).

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

Tests cover the evidence schema and provenance rules, pinned source values for
every study, percent-change arithmetic and signs, the duration model (anchors,
supported range, extrapolation and fallback flags), control availability per
study, page data, the evidence matrix and the HTTP server (including the
read-only rule). `tests/test_scenario_regression.py` compares the results
payload with a saved baseline (`tests/fixtures/scenario_baseline.json`) so that
interface changes cannot silently change the scientific output.

## Project structure

The browser only draws what the Python server sends; selection rules,
calculations and chart construction stay in Python.

- `app.py`, `server.py`: start the local server for `web/` and the JSON API.
- `simulator_model.py`, `data/simulator/`: 3D Simulator values and day evaluation.
- `api.py`: page data for the four pages; the Explorer has a controls-only
  view (`/api/scenario/controls`) and a full results view (`/api/scenario`).
- `evidence_catalog.py`: catalog loading, schema validation, harmonized series.
- `duration_model.py`: the multi-cohort and linear-fallback duration models.
- `scenario_inputs.py`: the five controls, study filter and option availability.
- `model.py`: assembles a scenario from the controls and the duration model.
- `plotting.py`: duration, recovery and comparison charts.
- `study_library.py`, `database.py`: SQLite schema and the eight study summaries.
- `build_evidence_matrix.py`: writes `docs/evidence_matrix.md`.
- `data/evidence/`: the catalog; `data/references/`: source PDFs.
- `web/`: pages, `assets/css/site.css` (theme tokens), `assets/js`,
  `assets/fonts/` (Inter, self-hosted, SIL OFL) and `assets/img/headers/`
  (decorative header images; sources and licences in `CREDITS.md`).
- `tests/`: test suites.

This is an educational research tool, not a clinical, operational, or
mission-planning system.
