# Atrophy Armour — Upgrade Task (Evidence Engine v2)

You are working on **Atrophy Armour**, an educational tool that organizes published evidence on skeletal-muscle changes in long-duration spaceflight. Act as a senior research software engineer with a scientist's discipline about evidence. You may redesign any part of the code base (Python modules, API, web pages, database schema, tests) if that is the cleanest way to deliver this task. Keep it an educational tool: it must never present itself as a clinical, operational, or mission-planning predictor.

Start in **plan mode**. Do Phase 0 and Phase 1 (read + research), then present a plan for my approval before writing code (see "Checkpoint" below).

---

## 0. Read first (ground truth)

Before anything else, read these completely:

- `README.md` — current scope, the evidence audit of English 2015 and Fitts 2010, and the reasons the duration slider was previously removed.
- `data/README.md` and `data/references/pdf_accessibility_report.md` — the inventory of all 8 reference PDFs, their identities/DOIs, which pages hold tables/figures, and known extraction pitfalls (merged cells, lost minus/± signs, decimals).
- `study_library.py`, `scenario_evidence.py`, `scenario_inputs.py`, `model.py`, `api.py`, `plotting.py`, `server.py`, `web/`, and `tests/`.

The 8 studies in the library are: English et al. 2015 (`amhp-article-pA68.pdf`), Fitts et al. 2010 (`tjp0588-3567.pdf`), Scott et al. 2023, Trappe et al. 2009, English et al. 2020 (NASA Sprint), LeBlanc et al. 2000, Gopalakrishnan et al. 2010, and Greene et al. 2021. Today the engine only uses English 2015 and Fitts 2010.

There are uncommitted changes in the working tree. Create a new branch (e.g. `evidence-engine-v2`) before you start editing, and do not discard or overwrite the existing uncommitted work.

---

## 1. Non-negotiable evidence rules (these override everything else)

1. **No unsourced science.** Every number, curve, slope, range, threshold, default, label of effect direction, and explanatory scientific sentence displayed or used in a calculation must trace back to either
   (a) one of the 8 reference PDFs (file, PDF page, table/figure, and the exact source wording or cell), or
   (b) an external source you actually opened during this session (full citation, DOI or URL, page/section/table, and the exact quoted value).
   Do not use values from memory or general knowledge, even if you are confident they are correct. If you cannot find a source, the value does not go in.
2. **Every derived value is labelled by type**, and that type is visible in the UI and stored in data:
   - `reported`: copied from a source as printed.
   - `calculated`: arithmetic on reported values (show the formula, e.g. percent change from pre/post means).
   - `digitized`: read off a published figure (state the figure, method/tool, and estimated reading error).
   - `approximation`: any interpolation, extrapolation, model fit, or assumption without a mathematical or scientific proof in a source. Each approximation must state what was assumed, why, what source data it is anchored to, and what would be needed to replace it.
3. **No pooling across incompatible evidence without saying so.** The studies differ in population (ISS vs. shuttle/Mir), biological level (fibre vs. muscle volume vs. whole-joint torque vs. trunk CT), baseline, timepoint, countermeasure, and statistic (mean ± SD vs. SEM vs. 95% CI, group means vs. individuals). Keep these attributes on every record. Results from different studies can be shown side by side on a common axis, but never averaged or merged into one value unless a cited method justifies it and the approximation is flagged.
4. **Keep the existing integrity conventions:** don't turn fibre counts into participant counts, don't infer individual values from group means/SDs, don't treat correlations as prediction equations, and keep postflight recovery days (R+x) separate from mission duration.
5. **Uncertainty travels with the value.** Wherever a source gives SD, SEM, CI, range, or n, store it and plot it. If it is not given, say "not reported". Never invent it.

---

## 2. Study-library constraint and the one allowed change

- **Do not add any new study** to the Study Library / reference table. The library stays at these 8 studies.
- External sources found online (Section 4) go into a separate **"External supporting evidence"** register (its own table/module and its own section on the Library page). They are cited supporting evidence, not new library studies. Keep the two lists clearly separate in code and UI.
- **Only allowed library change:** the Gopalakrishnan et al. (2010) entry is currently a one-page abstract (`data/references/Muscle volume, strength, endurance, and exercise loads during 6-month missions in space (2010) PDF.pdf`). Citation: *Aviation, Space, and Environmental Medicine* 81(2):91-104, DOI 10.3357/asem.2583.2010. Search for a full-text PDF available from a **legitimate** source: the publisher, PubMed Central, NASA NTRS, a university repository, or an author-posted copy. Do not use paywall bypasses or pirate sites (e.g. Sci-Hub). Before downloading, tell me the URL and file size and wait for my OK.
  - If found: verify it is the same article (title, authors, DOI, abstract text match). Save it in `data/references/`, keep the abstract file, update that one study record's source availability to full text, and extract its tables like the other studies. Also resolve the ambiguous calf-volume range "-10 to 16%" against the full text.
  - If not found: keep it as abstract-only, use only its abstract values (flagged as abstract-level), and list in the final report where you searched.

---

## 3. Phase 0 + 1: evidence extraction for all 8 studies (do this before UI work)

1. For every study, extract the quantitative results relevant to muscle atrophy and function into a single, unified, machine-readable evidence catalog (e.g. `data/evidence/*.json` or `*.csv` plus a loader with schema validation). Required fields per observation:
   `study_id, outcome_category, outcome_name, muscle/region, biological_level, unit, statistic_type (mean/median), value, dispersion_type (SD/SEM/95%CI/range/none), dispersion values, n and what n counts (crew / flights / fibres), cohort/subgroup, sex, countermeasure/hardware, mission_duration (value + dispersion as reported), baseline timepoint, measurement timepoint (preflight / R+0 / R+x days / in-flight day), source_file, pdf_page, table_or_figure, source_wording, value_type (reported/calculated/digitized/approximation), verification_status, notes/limitations`.
2. Read values from the rendered pages, not only from the PyMuPDF text layer. The audit says the text layer loses minus signs, ± signs, decimals, and cell alignment. Render the relevant pages to images and check each transcribed value visually. Record that check in `verification_status`.
3. Write automated tests that pin a sample of values per study to their source page/table, and a schema test that fails if any observation lacks provenance or a `value_type`.
4. Produce `docs/evidence_matrix.md`: rows are studies, columns are the harmonized measurement categories (Section 5), and cells show what is available (n, timepoints, statistic) or "not measured".

---

## 4. Mission-duration evidence research (external, required)

A previous attempt failed because there was not enough evidence to make a duration slider scientifically meaningful. Treat this as a research problem first.

1. Within the 8 studies, collect every link between mission duration and outcome. For example: LeBlanc 2000 has a ~17-day shuttle cohort and 16–28-week Mir cohorts; every study reports its own duration mean/SD/range; and any within-study correlation or regression with duration (check Scott 2023 in particular). Note that a study-level mean duration paired with a study-level mean change is one ecological data point, not a dose-response curve.
2. Then search the internet for credible sources on the time course of muscle loss versus unloading duration. Prioritize peer-reviewed papers and agency reports: NASA Human Research Program evidence reports on muscle risk, NASA technical reports (NTRS), ESA/Roscosmos publications, systematic reviews or meta-analyses of spaceflight and bed-rest muscle loss, studies with in-flight or multiple-duration measurements, and bed-rest/unloading analogue time-course studies. For each source, record the full citation, DOI/URL, the exact values used, and its population (spaceflight vs. analogue, countermeasure vs. none). Use WebSearch/WebFetch. Prefer open-access full text, and don't present anything you couldn't actually read.
3. Pick the most defensible duration model **per outcome category**, in this order of preference:
   a. A published time-course function or rate taken directly from a source (cite the equation/values).
   b. A fit to multiple real data points across durations (show the points, the fit, and goodness-of-fit, and flag it as `approximation` if it is your fit rather than a published one).
   c. **Fallback:** linear scaling between a defined anchor (0 days = 0 change) and the reported observation at the reported mission duration. Allowed only if (a) and (b) are not credible for that outcome.
4. Analogue (bed-rest) evidence may inform the *shape* of a time course only if the UI clearly labels it as ground-analogue evidence, not spaceflight data.
5. Never extrapolate silently beyond the duration range covered by the data. Outside the supported range, either clamp or show a prominent "extrapolation" warning, and visually distinguish extrapolated segments (e.g. a dashed line).
6. If you use the linear fallback anywhere, say so: (i) a persistent, plain-language notice on the main page next to the slider and in every affected chart's caption/legend, (ii) a `value_type = approximation` flag on every affected output, and (iii) a section in the final report (Section 8).

---

## 5. Measurements page: harmonized across all studies

Redesign the Measurements page so every study is viewed through the **same set of measurement categories**, in the same order and layout, so studies can be compared. Use the README's relevance focus (muscle atrophy, strength, recovery, countermeasures). A suggested set, which you may adjust only if the evidence matrix justifies it:

1. **Muscle size**: volume or cross-sectional area (MRI/CT), by region (thigh, calf, trunk/paraspinal, etc.).
2. **Whole-joint strength**: isokinetic/isometric torque by joint and movement.
3. **Muscle endurance / work capacity**: total work, fatigue indices.
4. **Fibre-level properties**: fibre diameter/CSA, peak force, velocity, power, by fibre type.
5. **Body composition**: lean mass, fat mass, muscle attenuation/quality (DXA/CT).
6. **Aerobic capacity**: VO2peak or similar (when reported).
7. **Recovery**: postflight time course for any of the above.

Requirements:

- Each study shows every category. If a study did not measure something, show "Not measured in this study" rather than hiding it, so all studies have the same number of category slots.
- Within each category, normalize the presentation the same way across studies: percent change from the study's own baseline (calculated when needed, with the formula shown), plus the original reported value and unit, statistic, dispersion, n (and what n counts), timepoint, and provenance link.
- Provide filters for category, region, study, and timepoint, and an interactive comparison chart per category (studies side by side, never merged).
- Keep the existing ability to add/verify manual records, now using the unified schema.

---

## 6. Main page (Scenario Explorer) requirements

### 6.1 Five interactive variables

Implement exactly five scientific input controls (separate from the duration slider) that change what is computed and displayed. I suggest the five below. Keep them if the evidence supports them, and if one is not supported by the extracted data, replace it and explain why in the plan:

1. **Outcome category**: the harmonized categories from Section 5.
2. **Muscle group / region**: thigh/knee, calf/ankle, trunk, whole body, and so on, filtered to what the selected category has data for.
3. **Countermeasure / exercise regimen**: for example, pre-ARED (iRED) vs. ARED era (English 2015), Sprint high-intensity vs. standard ISS exercise (English 2020), shuttle/Mir-era cohorts (LeBlanc 2000), and the exercise descriptions in Trappe/Fitts/Scott.
4. **Crew subgroup**: all / men / women, where reported.
5. **Postflight recovery day**: R+0 through the latest follow-up available (e.g. Greene's multi-year follow-up), snapping to reported timepoints. Only use interpolation if it is flagged as approximation.

Also include a **study selector** (one study, or "compare all studies that report this"). Treat it as a filter, not one of the five variables.

Each control must:

- disable or grey out options with no data, and show the reason (e.g. "Not reported by Greene 2021"),
- never fabricate a value for an unsupported combination,
- show which study/table each displayed number came from.

### 6.2 Mission-duration slider

- The range and default **depend on the selected study and outcome**, derived from the reported durations (and the duration model's supported range from Section 4).
- Moving it must change the displayed outcome through the Section 4 model, not only update context text.
- Show the model type next to the slider (published function / fitted / linear approximation), its sources, and the supported range. Show an extrapolation warning outside that range.

### 6.3 Interactive graphs

- Every calculated or displayed quantitative outcome is also shown as an interactive chart where a chart makes sense. Use Plotly (already used; check that `web/assets/vendor/plotly.min.js` actually exists and is served, and fix it if not).
- Charts must have hover tooltips with value, unit, dispersion, n, timepoint, value_type, and source; error bars/bands wherever uncertainty is reported; and visible distinctions between reported points, fitted/approximated curves, analogue-derived curves, and extrapolated segments.
- Include at least: (a) outcome vs. mission duration (with the model curve and the real anchor points), (b) recovery over postflight days, (c) a cross-study comparison for the selected category.

---

## 7. UI simplification for the development period

Strip decorative styling so development is fast and the UI is easy to read:

- Remove the Google Fonts links and use the system font stack.
- Remove text/reveal/motion animations (`motion-boot.js`, `reveal.js`, CSS transitions, keyframes, and animations).
- Reduce the palette to neutral greys plus one accent colour, keeping only colours that carry meaning (warning/approximation/extrapolation states, chart series).
- Keep the layout clean, accessible, and responsive. Leave short comments marking where visual design can be reintroduced later.

---

## 8. Architecture, testing, and verification

- Keep scientific logic in Python (the browser only renders what the API returns), unless you have a strong reason to change this, which you must state in the plan.
- Update or replace tests to cover the evidence schema/provenance, value pinning per study, percent-change arithmetic and signs, the duration model (including anchors, supported range, extrapolation flags, and fallback flagging), control availability per study, the API, and the server.
- Run `python -m pytest` and report the actual results.
- Start the app (`python app.py`), exercise every control and slider in a browser, and confirm the charts update and the approximation/extrapolation notices appear where expected.
- Update `README.md` and `data/README.md` to describe the new evidence model, controls, duration model, and limitations.

---

## Checkpoint (stop here once, before implementation)

After Phases 0–1 and the Section 4 research, present for approval:

1. the evidence matrix (studies × categories),
2. the Gopalakrishnan full-text search result,
3. the duration-model decision per outcome category, with sources, and where the linear fallback will be used,
4. the final list of five variables and any substitutions,
5. the file/architecture changes you intend to make.

Then wait for my approval.

---

## 9. Final report (your last message when done)

Structure it as:

1. **Summary of changes**: files and features.
2. **Study coverage**: per study, what was extracted, how many observations, and which categories they fill.
3. **Gopalakrishnan 2010**: whether the full text was found (source URL) or where you searched.
4. **External supporting evidence**: a numbered list with citation, DOI/URL, and what each was used for.
5. **Mission-duration model**: per outcome, which model is used and why.
6. **If any linear approximation is used**: a plain-language section (no jargon, readable by a non-scientist) explaining what is missing in the evidence, why that prevents a real duration curve (for example, too few measurements at different mission lengths, no in-flight measurements, results mixed with different exercise regimes), what the linear line assumes, and what kind of data would fix it.
7. **All approximations and digitized values**: a complete list with their justification.
8. **Known limitations and open questions.**
9. **Test results and manual verification performed**, including anything you could not verify.
