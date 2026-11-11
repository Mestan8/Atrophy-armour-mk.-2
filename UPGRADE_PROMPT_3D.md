# Atrophy Armour — Upgrade Task 2: "3D Simulator" page (soleus, fibre-level atrophy)

You are working on **Atrophy Armour**, an educational tool that organizes published evidence on skeletal-muscle changes in long-duration spaceflight. Act as a senior graphics/front-end engineer who is also trained in muscle physiology, with a scientist's discipline about evidence. The audience for this page is a **master's-level physiology student**: the anatomy and ultrastructure must be correct enough to pass review by a muscle physiologist, and every change shown during the simulated mission must trace back to data.

Start in **plan mode**. Do Phase 0 (read) and Phase 1 (evidence + research), then stop at the Checkpoint and present a plan before writing code.

Keep everything that already works. Do not change the Scenario Explorer (now a two-step "Scenario → Show results" page), the read-only Measurements page, or the Study Library page, except to add the new page to the shared navigation. Create a new branch (e.g. `3d-simulator`) from the current branch (`ui-two-step-explorer`). Earlier upgrades may still be uncommitted in the working tree; do not discard or overwrite them, and do not touch `UPGRADE_PROMPT*.md` or `FIX_PROMPT*.md`.

---

## 0. Read first

- `UPGRADE_PROMPT.md`: the evidence-engine upgrade. Its evidence rules (Section 1) still apply here, with the exceptions in Section 2 below.
- `UPGRADE_PROMPT_3.md` and `FIX_PROMPT_STALE_SERVER.md`: the two most recent changes. These added the two-step explorer with its `/api/scenario/controls` + `/api/scenario` split, a GET-only server (POST → 405), removed manual records, and added `/api/health` with `API_VERSION`, exclusive port binding on Windows, and the out-of-date-server notice.
- `README.md`, `data/README.md`, `docs/evidence_matrix.md`, `data/references/pdf_accessibility_report.md`.
- `data/evidence/fitts-2010.json`, `data/evidence/trappe-2009.json`, `data/evidence/external_sources.json`, `data/evidence/duration_evidence.json`.
- `evidence_catalog.py` (note its `VALUE_TYPES` set and validation), `duration_model.py`, `api.py`, `server.py` (note how static files are served, and that Plotly is served from the installed Python package at `/assets/vendor/plotly.min.js`; no `web/assets/vendor/` folder exists on disk), `web/` (in particular `site-header.js`, `core.js`, `site.css`, `explorer.js`), and `tests/`.
- The two primary PDFs, in full:
  - **Fitts et al. (2010)**, *Prolonged space flight-induced alterations in the structure and function of human skeletal muscle fibres*, J Physiol 588(18):3567–3592 (`data/references/tjp0588-3567.pdf`).
  - **Trappe et al. (2009)**, *Exercise in space: human skeletal muscle after 6 months aboard the International Space Station*, J Appl Physiol 106:1159–1168 (`data/references/Exercise in space human skeletal muscle after 6 months aboardthe International Space Station (2009.pdf`; same 9 ISS crew members).

Read the PDFs again for this task. Do not rely only on the existing JSON. The JSON was built for the Scenario Explorer and holds mostly Fitts Tables 2–6 and Trappe Table 5. The 3D model needs more: fibre-type distribution, any electron-microscopy or ultrastructure findings (for example myofilament/thin-filament density or spacing, myofibril or sarcomere changes), specific tension, power, peak force normalized to CSA, and anything Fitts or Trappe report about capillaries, nuclei, fibre hybrids, or the high- vs low-treadmill subgroups. List every soleus-relevant value you find, with its page and table/figure.

What already exists (check it, don't trust it): soleus type I fibre diameter 98 ± 1 → 79 ± 1 µm (all crew, Fitts Table 2, mean ± SEM, n = fibres), soleus type I/II CSA, Po and Vo; soleus muscle volume 455 ± 27 → 383 ± 19 cm³ at R+4 (−15 ± 2 %) and 408 ± 20 at R+19 (Trappe Table 5); soleus MHC I fibre share −17 ± 6 % (Trappe text). Mission duration 177 ± 4 days (range 161–192).

---

## 1. Goal

Build a new page, **"3D Simulator"** (`web/simulator.html`, nav label "3D Simulator"), showing an interactive, real-time 3D model of the **human soleus**. The user can zoom continuously from the whole lower leg down to the inside of a single muscle fibre. A **mission-duration slider** (day 0 → end of mission) changes the model's geometry and properties so the user can see unloading-induced atrophy develop. The changes are driven by Fitts 2010 and Trappe 2009.

This is a visualization of published group-mean data, not a prediction for an individual. Say so on the page.

---

## 2. Evidence rules for this page

The rules in `UPGRADE_PROMPT.md` Section 1 apply in full (no unsourced science, `value_type` labels, uncertainty travels with the value, no fibre-count-as-participant-count). Here is what is different or added for this page:

1. **Primary data sources:** Fitts 2010 and Trappe 2009. Every atrophy-driven parameter (what changes with the slider) must come from these two, unless a value they don't report is needed. In that case, take it from an external source and flag it.
2. **External sources are allowed** for (a) normal human soleus anatomy and ultrastructure (architecture, pennation, fibre-type proportions, sarcomere dimensions, filament lattice spacing, myonuclear domain, mitochondrial volume fraction, capillary density, and so on), and (b) the shape of the time course between launch and landing (see Section 4). Use peer-reviewed papers, standard physiology/anatomy references, or agency reports that you actually opened in this session (WebSearch/WebFetch). Never use values from memory.
3. **Do NOT add any source to the Study Library / reference table, and do not build a bibliography or references page.** That comes later. Still record provenance internally, because the later references page will be generated from it: put every value the simulator uses in one machine-readable file (e.g. `data/simulator/soleus_parameters.json`), with fields for value, unit, dispersion, n and what n counts, `value_type` (`reported` / `calculated` / `digitized` / `approximation` / `illustrative`), source (study_id, or full citation + DOI/URL for external), page/table/figure, and the exact quoted wording. Do not register these in `external_sources.json` or the library.
4. **New value type `illustrative`.** Some geometry cannot be data-driven at real scale. The human soleus has on the order of 10⁵–10⁶ fibres, and each fibre has thousands of myofibrils. Render a representative sample: proportions and dimensions come from data, but counts and exact placement are illustrative. Every rendered element that is illustrative rather than measured must be labelled as illustrative in its info panel. Real dimensions and ratios must stay correct (e.g. fibre diameter relative to sarcomere length, type I : type II proportion), even when counts are reduced. `illustrative` is not in `evidence_catalog.VALUE_TYPES`. Keep the simulator parameters in their own file and validator so the evidence catalog, Scenario Explorer and Measurements page are unaffected. If you decide to add it to the shared set instead, explain why at the Checkpoint and prove the existing pages' output is unchanged.
5. **Timepoint honesty.** Fitts biopsies are R+0 (landing day). Trappe MRI is R+4 and R+19. None of these are in-flight measurements. The end-of-mission state must say which postflight timepoint each value comes from. Do not present R+4 volume as an in-flight value without saying so.
6. **Subgroups.** Fitts reports high-treadmill (n = 4) and low-treadmill (n = 5) subgroups. If you offer them as a toggle, keep their n visible and never mix subgroup values with all-crew values in the same render.

---

## 3. Scale levels (zoom design)

Implement continuous zoom (scroll / pinch / buttons) through these levels. Use LOD transitions so detail appears as you approach. Each level has a short caption, labelled structures (leader-line labels like reference image 1), and a click-to-inspect info panel. Adjust the boundaries if the research gives you a reason, and explain it at the Checkpoint.

| Level | Scale | What is rendered | Data-driven by the slider |
|---|---|---|---|
| **L0 Leg / anatomy** | ~40 cm | Lower leg, posterior view, semi-transparent skin. Tibia, fibula, calcaneus, Achilles tendon, gastrocnemius (ghosted/toggleable, since it overlies the soleus), **soleus highlighted** like reference image 3. Correct origin (posterior fibular head/upper fibula, soleal line and medial border of tibia, tendinous arch) and insertion via the Achilles tendon into the calcaneus. | Soleus volume (Trappe), scaled so the shape is kept and the volume ratio matches the data. |
| **L1 Whole-muscle cross-section** | ~5 cm | A cut through the soleus belly like the lower half of image 1: epimysium, fascicles packed in perimysium, blood vessels and nerves in the connective tissue. Show the soleus's multipennate/bipennate internal architecture (verify against an anatomy source). | Fascicle/fibre packing derived from the CSA change. Say how this is calculated. |
| **L2 Fascicle** | ~1 mm | Bundle of fibres with endomysium and capillaries between fibres. Type I and type II fibres distinguishable (toggleable colour coding), in data-correct proportions. | Fibre diameter per type (Fitts Table 2 and fibre-type tables), MHC I share (Trappe). |
| **L3 Single fibre** | ~100 µm | Style of reference image 2: translucent sarcolemma, peripheral myonuclei (purple), subsarcolemmal and intermyofibrillar mitochondria (orange), myofibrils with visible striation, cutaway window, sarcoplasmic reticulum and T-tubule triads at the A–I junction (verify placement for human muscle). | Fibre diameter/CSA, and myofibril count/packing if Fitts reports ultrastructure. Otherwise flag the inference as `approximation`. |
| **L4 Myofibril / sarcomere** | ~2–3 µm | One sarcomere in longitudinal view (Z-discs, I-band, A-band, H-zone, M-line, thick myosin and thin actin filaments, titin) plus a cross-section showing the hexagonal thick–thin lattice. | Any thin-filament density/spacing change Fitts reports from EM. If they report none, say "not measured" and do not change this level. |

Interaction requirements:
- Orbit, pan, zoom; a level indicator / breadcrumb (Leg › Muscle › Fascicle › Fibre › Sarcomere) that you can click to jump; a "reset view" control; a scale bar that updates with zoom.
- Click any structure → info panel: name, function (one or two sentences, sourced), current value vs preflight, % change, dispersion, n, timepoint, `value_type`, and source.
- **Compare mode:** show the preflight geometry as a ghost outline (or a split / side-by-side view) over the current day, so the atrophy is visible even when it is small.
- Optional overlay: colour-map structures by % change from preflight, with a legend.

---

## 4. Mission-duration slider and time course

- Range: day 0 → the mission duration of the source cohort (177 days mean, 161–192 range). Decide whether the slider stops at 177 or 192 and justify it. Beyond the supported range, either clamp or show a prominent extrapolation warning, following the same convention as `duration_model.py`.
- Day 0 = preflight values, end of mission = the reported postflight values (with their timepoint caveat from Section 2.5).
- **Between the two, there are no in-flight data in Fitts or Trappe.** Pick the time-course shape using the same order of preference as `UPGRADE_PROMPT.md` Section 4: (a) a published time-course function, (b) a fit to multi-timepoint data (bed-rest/unloading analogues allowed only if labelled as analogue evidence and used only for the *shape*, scaled to the Fitts/Trappe endpoints), (c) a linear fallback. Reuse or extend `duration_model.py` rather than writing a second model. Whatever you pick, show the model type and a plain-language notice next to the slider, and flag every interpolated value as `approximation`.
- Different parameters may follow different curves only if a source supports it (e.g. if fibre CSA is known to decline earlier/faster than whole-muscle volume). Otherwise use one shared shape.
- Also include a recovery control or display only if you can do it with reported data (Trappe R+19). Snap to reported timepoints and do not interpolate recovery unless flagged.
- Play/pause button to animate the mission at a sensible speed, with the day counter visible.
- Unlike the Scenario Explorer, this page has no "Show results" step: the model and its controls are visible and live on load, and the slider updates the 3D scene directly (debounced API calls, with a latest-request guard like `explorer.js`). If a cohort/subgroup toggle is offered, changing it also updates live.

---

## 5. Visual style

Match the attached reference images:
- **Image 1 (structure hierarchy):** deep teal/green radial-gradient background, realistic red muscle with subtle connective-tissue sheen, cut faces showing marbled fascicles, thin white leader lines with small circle endpoints and clean sans-serif labels.
- **Image 2 (single fibre):** translucent glassy sarcolemma with soft highlights, red striated myofibrils, purple ellipsoid nuclei, orange mitochondria with visible cristae pattern, rectangular cutaway window.
- **Image 3 (anatomical context):** clinical anatomy-atlas look with bone, white ligaments/tendons, and the target muscle highlighted in a saturated cyan inside a translucent body outline.

Use physically based materials (MeshPhysicalMaterial with transmission/clearcoat where appropriate), soft studio lighting, and subtle ambient occlusion. Generate geometry procedurally, or with models whose license allows redistribution (state the license in the plan). Do not copy the reference images or textures from them; they show the style only.

This page may have its own richer styling. The "strip decorative styling" rule from the previous upgrade applies to the other pages, not to the 3D canvas. Keep the page chrome (header, panels) consistent with `site.css`.

---

## 6. Architecture

- **Rendering:** Three.js with a pinned version, **committed as a real file** in the repo (e.g. `web/assets/vendor/three/`), with no CDN at runtime. Plotly works differently: `server.py` generates it from the Python package, and no such package exists for Three.js. Before downloading Three.js, tell me the exact version, source URL and file size, and wait for my OK. Check that `server.py`'s static handling serves the new files with the correct MIME type (`.js`/`.mjs` as `text/javascript`, plus any `.glb`/`.json` assets) without breaking the special Plotly route. Use ES modules or a single bundled file, with no build step unless you justify one.
- **Science stays in Python:** add a GET endpoint to `_GET_ROUTES` (e.g. `GET /api/simulator/soleus?day=…&cohort=…`) that returns, for that day, every parameter value with its full provenance and `value_type`. The server stays GET-only. Bump `API_VERSION` in `api.py` so the existing out-of-date-server check catches a stale server, and give the new page the same "server is outdated, restart it" notice the explorer has. The browser only turns parameters into geometry. The procedural geometry may compute derived visual quantities (e.g. a radius from CSA), but must not hold any scientific constants of its own: those come from the parameters file via the API.
- **Performance:** target 60 fps on an integrated laptop GPU. Use instanced meshes for fibres, myofibrils, mitochondria and filaments, LOD/frustum culling, and only build each level's detail when you approach it. Debounce the slider. Show a clear message if WebGL is unavailable.
- **Accessibility:** keyboard controls for zoom/level/slider, `prefers-reduced-motion` respected (no auto-rotation, play is user-initiated), and a text panel that lists the current values so the information is not only visual.
- Add the page to `PAGES` in `site-header.js` and to the server routes.

---

## 7. Tests and verification

- Pytest: every parameter in the simulator file has a source and `value_type`; the API's day 0 values equal the preflight values and its end-of-mission values equal the reported postflight values (pin these to the Fitts/Trappe numbers); interpolated days are flagged `approximation`; out-of-range days are clamped or flagged; and illustrative elements are marked illustrative. Also update the server tests for the new route.
- Run `.\.venv\Scripts\python.exe -m pytest` (PowerShell script activation is blocked on this machine, so call the venv's Python directly) and report the real results. All existing tests must still pass, including the scenario regression test.
- Stop any running Atrophy Armour server, start one fresh with `.\.venv\Scripts\python.exe app.py --no-browser`, open the page in the browser, and **take screenshots at each zoom level at day 0 and at end of mission**, plus compare mode. Check the console for errors and measure frame rate at L2/L3. Fix what you see before reporting.

---

## Checkpoint (stop here once, before implementation)

Present:
1. The full list of soleus parameters you will use, as a table: parameter, preflight value, postflight value, unit, dispersion, n, timepoint, source (Fitts/Trappe page+table, or external citation), `value_type`, and which zoom level uses it.
2. Which ultrastructural changes Fitts/Trappe actually report, and which levels will therefore change versus stay unchanged ("not measured").
3. External sources found for normal soleus anatomy/ultrastructure and for the time-course shape, with what each provides.
4. Your time-course model decision and the slider range.
5. The zoom-level design (any changes to the table in Section 3), the rendering approach per level, and the asset/license plan.
6. Files to be added or changed.

Then wait for my approval.

---

## Final report

1. Summary of what was built (files, features).
2. Parameter table (final version of Checkpoint item 1).
3. What is data-driven vs illustrative at each zoom level.
4. Time-course model, and a plain-language explanation of what the in-between days assume.
5. All approximations and external values, with justification.
6. Known scientific limitations (e.g. biopsy site vs whole muscle, R+0/R+4 timing, group means, representative fibre counts).
7. Test results and the screenshots/manual checks you performed, including anything you could not verify.
