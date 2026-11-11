# Atrophy Armour — Upgrade Task 3: two-step Scenario Explorer and read-only Measurements page

You are working on **Atrophy Armour**, an educational tool that organizes published evidence on skeletal-muscle changes in long-duration spaceflight. Act as a senior front-end/full-stack engineer. This task changes **page structure and reading flow only**:

- No scientific value, calculation, duration model, evidence record, provenance, or label may change.
- The same scenario selection must produce exactly the same numbers, charts, notices, and source statements as before.
- Visual design is out of scope. Keep the current plain styling. Add only the minimum CSS needed for the new structure to read clearly.

Before editing, briefly state your plan (files to change, API shape, and how you will prove the outputs are unchanged), then implement. Stop and ask only if something in this prompt conflicts with what you find in the code.

---

## 0. Read first

- `README.md`, `data/README.md`
- `web/index.html`, `web/assets/js/explorer.js`, `web/assets/js/core.js`
- `web/measurements.html`, `web/assets/js/measurements.js`
- `api.py` (especially `build_scenario_view`, `build_measurements_view`, `add_measurement_record`, `verify_measurement_record`), `server.py`, `manual_records.py`
- `tests/` (especially `test_scenario.py`, `test_server.py`, and any tests that cover manual records)

Work on a new branch (e.g. `ui-two-step-explorer`). The working tree has uncommitted work from earlier upgrades. Do not discard or overwrite it, and do not touch `UPGRADE_PROMPT*.md`.

---

## 1. Scenario Explorer: settings first, results on confirmation

Today the page shows the controls and the results side by side, and the results update on every change. Change it to a two-step, top-to-bottom flow.

### Step 1: "Scenario" (the only thing visible on first load)

- The page shows the title and short intro, then a **Scenario** section with the study filter, the five scientific input controls, and the "Reset scenario to defaults" button.
- Keep the existing dependent-option behaviour: when one control changes, the server still recalculates which options are valid and greys out unsupported options with the reason. This must stay live, without the confirm button.
- At the end of the section, add a primary button labelled **"Show results"**.
- **The mission-duration slider moves out of this section** into Step 2.

### Step 2: "Results" (hidden until the button is pressed)

- Pressing **Show results** reveals, below the Scenario section and in this order:
  1. the result summary and result rows (values, value-type tags, warnings, provenance buttons),
  2. the **mission-duration slider** with its model label, range text, notices, supported range, source statements, and sources,
  3. the three charts (outcome vs. mission duration, recovery over postflight days, cross-study comparison),
  4. the three collapsible explanation panels (duration model, external supporting evidence, value-type labels).
- After revealing, scroll the Results heading into view and move keyboard focus to it (`tabindex="-1"`), so keyboard and screen-reader users land there too.
- Inside Results, the **duration slider keeps updating the results and charts live** (same debounced behaviour as now). The slider is part of reading the results, not part of the scenario.

### State rules (implement exactly)

| Situation | Behaviour |
|---|---|
| First visit | Scenario at defaults; Results hidden. |
| Reload with a saved selection in localStorage | Restore the saved Scenario selections; Results stay hidden until the button is pressed. Do not store the "results shown" state. |
| Scenario control changed while Results are shown | Do **not** silently recalculate the results. Keep them visible, mark them clearly as out of date with a notice at the top of Results ("Scenario settings changed — press Update results to recalculate."), visually de-emphasize them, and relabel the button **"Update results"**. Pressing it recalculates and clears the notice. |
| Scenario control changed so the duration default changes | When the results are next confirmed, the slider resets to the new study's default, as it does today. |
| "Reset scenario to defaults" | Restore defaults, clear the saved selection, and hide Results. |
| Request in progress | Disable the button and show a short "Loading…" state. Ignore stale responses (keep the existing latest-request guard). |
| Request fails | Show the error inside Results. Do not leave the old results looking current. |

### API

- Changing a control should not compute the charts. Split the work so that control changes fetch only the **control state** (options, availability, reasons, defaults), and the confirm button or the slider fetches the **full results**. You can split the endpoint (e.g. `/api/scenario/controls` and `/api/scenario`) or add a parameter. Choose the cleaner one and explain it.
- All selection rules and calculations stay in Python. The browser only renders what the API returns.
- The results payload for a given selection must be **identical** to what `build_scenario_view` returns today. Add a regression test that compares the old and new output for several selections across different studies and categories, including one with a linear-approximation duration model and one outside the supported duration range.

---

## 2. Measurements page: remove manual record entry

Remove the **"Add a manual record"** feature completely. The Measurements page becomes read-only:

- Remove the `#add-panel` form and the `#verify-panel` "Mark a manual record as checked" form (it only exists to serve manual records), the `#form-status` element, and their JavaScript.
- Remove the **"Manual records"** list from each study card, and the `manual` field from the measurements API payload.
- Remove the POST routes `/api/measurements` and `/api/measurements/verify`, plus `add_measurement_record` and `verify_measurement_record` in `api.py`. The server should then answer only GET requests; any POST should return `405 Method Not Allowed`. Add a test for this.
- Remove `manual_records.py` and its tests if nothing else uses them. Search the code first, and if something else does use it, report what instead of deleting it.
- **Do not delete or alter data in the SQLite database.** Leave any existing manual-record table and rows untouched. In the final report, state how many manual records exist in the local database (read-only query), so I can decide what to do with them.
- Update `README.md` and `data/README.md`. Remove the instructions that say to add values through the Measurements page, and explain that evidence is now added only through the curated catalog in `data/evidence/` with its schema validation and tests. Also remove the README warning that anyone who can reach the server can add or verify records, since that is no longer possible.

---

## 3. Verification

1. Run `python -m pytest` and report the actual results.
2. Start the app (`python app.py --no-browser`) and check in a browser:
   - first load shows only the Scenario section;
   - changing controls still greys out unsupported options live without showing results;
   - **Show results** reveals results, slider, charts, and panels in the specified order, and focus lands on the Results heading;
   - the slider updates the results and charts live;
   - changing a control after confirming shows the out-of-date notice and the "Update results" label;
   - Reset hides Results;
   - reloading restores the settings but not the results;
   - the Measurements page has no add or verify forms and no manual-record lists, and its filters and charts still work;
   - there are no console errors.
3. Check the layout at a phone width (about 375 px).

---

## 4. Final report

1. Summary of changes by file.
2. The API shape you chose, and why.
3. Proof that the scientific output is unchanged (which regression test does this, and which selections it covers).
4. What was removed for the Measurements change, including the manual-record count in the database.
5. Test results and the browser checks performed, and anything you could not verify.
