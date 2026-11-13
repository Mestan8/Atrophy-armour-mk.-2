# Atrophy Armour — Upgrade Task 4: rename to "Atrophy Armour Mk. 2" and a light visual theme

You are working on **Atrophy Armour**, an educational tool that organizes published evidence on skeletal-muscle changes in long-duration spaceflight. It has four pages: Scenario Explorer, Study Library, Measurements and 3D Simulator. Act as a senior front-end engineer with a good eye for restrained, scientific UI design.

This task is **naming and presentation only**:
- No scientific value, calculation, evidence record, provenance, label, control behaviour or API payload may change. The scenario regression test must pass unchanged.
- **No wording may be added, removed or reworded** anywhere on the pages (headings, intros, help text, buttons, notices, captions), except the product name in Section 1. You may change sizes, weights, fonts, colours, spacing, borders and layout polish only.

Before editing, give a short plan (files to change, the colour tokens, the font choice, and the background-image candidates from Section 3), then **wait for my OK**, because the images and font need downloads. After that, implement without stopping again unless something here conflicts with the code.

Create a new branch (e.g. `ui-mk2-theme`) from the current branch. If there are uncommitted changes when you start, stop and tell me rather than carrying them over or discarding them. Do not edit `UPGRADE_PROMPT*.md`, `FIX_PROMPT*.md` or `environment_test.md`: they document earlier iterations and keep the old name on purpose.

---

## 0. Read first

- `README.md`, `data/README.md`
- `web/*.html`, `web/assets/css/site.css`, `web/assets/css/simulator.css`, `web/assets/js/site-header.js`, `web/assets/js/core.js`, and wherever Plotly chart layouts/colours are set (JS or Python)
- `web/assets/js/sim/` (only to read the 3D scene's palette: background teal/dark gradient, cyan highlighted soleus `0x14c4d4`, white leader lines)
- `app.py`, `server.py`, `api.py`, and `tests/` (especially any test that asserts on a message containing the product name)

---

## 1. Rename to "Atrophy Armour Mk. 2"

The exact new name is **`Atrophy Armour Mk. 2`**. Use this spelling and capitalization everywhere.

Replace every reference to the current iteration of the product:
- the `<h1>` in `site-header.js` and every page `<title>` (e.g. `Scenario Explorer · Atrophy Armour Mk. 2`),
- user-facing messages in JS and Python (e.g. "The Atrophy Armour Mk. 2 server is not responding…", the startup line printed by `app.py`, the port-in-use error in `server.py`), plus the docstrings and CLI help that name the product,
- `README.md` and `data/README.md` (title and body text that describes the current tool),
- tests that assert on those messages (update the expected strings, nothing else).

Do **not** rename: the project folder, the git repository, Python module/function names, URL paths, API routes, JSON keys, data files, the localStorage keys (renaming would wipe users' saved scenarios; if a key contains the old name, leave it and add a comment saying why), or the historical prompt files listed above. Where the README describes history (e.g. "Atrophy Armour Mk. 1 used Streamlit…"), you may refer to the earlier version as "Atrophy Armour (Mk. 1)".

Finish with a case-insensitive search for `atrophy armour` (excluding `.venv`, `.git` and the historical prompt files) and list every remaining hit with the reason it stays.

---

## 2. Visual theme: dark blue, white, cyan

Goal: simple, clean and visually appealing, consistent with the 3D Simulator's look, and light enough to load instantly. No frameworks, no build step, no new JS libraries.

**Palette.** Define everything as CSS custom properties in `site.css` (it already has `DESIGN HOOK` comments for this):
- dark navy/deep blue for the header band and primary surfaces (around `#0b1f3a`–`#10294d`),
- white for text on dark and for content panels,
- cyan accent taken from the simulator's soleus highlight (`#14c4d4` or a close tone that passes contrast), used for links, the active nav item, focus rings, slider thumbs, primary buttons and small highlights,
- a light cool-grey/blue-tinted page background so the dense data areas (tables, result rows, charts) stay easy to read; don't make the whole app dark.
- **Keep every colour that carries meaning** (approximation amber, extrapolation/error red, the value-type tags, the % change colour scale, chart series colours). You may adjust their shade to fit the theme, but each must stay distinguishable from the others and from the accent, and pass WCAG AA contrast.
- Check contrast for all text/background pairs (≥ 4.5:1 for body text, ≥ 3:1 for large text and UI borders), and list the main pairs with their ratios in the final report.

**Typography.** Change fonts and sizes only:
- One clean sans-serif family for UI and headings (e.g. Inter, IBM Plex Sans or Source Sans 3), **self-hosted** as `.woff2` in `web/assets/fonts/` under the SIL Open Font License, with its license file next to it. No Google Fonts or CDN at runtime. Before downloading, tell me the family, weights, source URL and total size, and wait for my OK. Keep the system font stack as the fallback, and keep the monospace stack for numbers.
- Use a clear type scale (e.g. h1 ≈ 32–40 px on desktop, h2/h3/body stepping down, body ≥ 15 px). Use tabular figures (`font-variant-numeric: tabular-nums`) where numbers line up (results, tables, slider value).

**Components (light touch).** Rounded panels with a subtle shadow or 1 px border, consistent spacing, styled buttons (primary = cyan on navy text, or navy with cyan hover, whichever passes contrast), styled `select`/inputs/range slider, and a clear focus ring. At most, short colour/shadow hover transitions (≤ 150 ms), disabled under `prefers-reduced-motion`. No scroll or reveal animations, no parallax, no glassmorphism-heavy effects.

**Charts.** Make the Plotly charts match the theme: font family, axis/grid/label colours and background. Do **not** change series colours that encode meaning (reported vs fitted vs approximation vs extrapolated vs analogue), marker shapes, dash styles, error bars, or any data.

**3D Simulator page.** Only restyle the page chrome (header, side panels, buttons, slider, info panel) to the shared theme. Do not change the 3D scene, its materials, lighting or canvas background, except to swap hard-coded chrome colours in `simulator.css` for the shared tokens.

Remove or rewrite the "plain development styling" comment at the top of `site.css` so it describes the new theme, and keep the `DESIGN HOOK` markers.

---

## 3. Header background images (one per page)

Behind the `Atrophy Armour Mk. 2` heading on every page, the header band gets a background image, **different on each page** and relevant to it. Suggested subjects (you may propose better ones):

| Page | Suggested subject |
|---|---|
| Scenario Explorer | an astronaut exercising on the ISS (treadmill, cycle ergometer or ARED), or the ISS in orbit |
| Study Library | a scientific/research image: a lab, archival spaceflight research, or Earth from orbit |
| Measurements | an imaging/measurement subject: an MRI of the lower leg/thigh, a muscle histology cross-section, or a crew member doing a strength/muscle test |
| 3D Simulator | a still rendered from this project's own 3D Simulator (e.g. the cyan soleus at Leg level, or the fibre level), captured from the running app. No licence needed. |

Rules:
- **Licensing:** use only images you can redistribute without on-page credit, so that no text has to be added to the pages: NASA imagery (generally public domain; check the specific item's page, because some NASA-hosted images belong to third parties), other public-domain or CC0 sources, or renders of our own simulator. Avoid CC BY / CC BY-SA images, since they need visible attribution. At the plan step, list each candidate with its source page URL, author/agency, licence and file size, and wait for my OK before downloading.
- Record each image's source URL, author, licence and retrieval date in `web/assets/img/headers/CREDITS.md` (a repo file, not shown on the pages, not added to the Study Library or reference table).
- **Presentation:** apply the image with CSS (`background-image` on the header band, chosen per page through `body[data-page]`), not as an `<img>` in the content, so it is purely decorative and adds no text. Put a dark-navy gradient overlay over it so the white heading, nav and intro text stay readable (verify the contrast over the brightest part of each image). Use `background-size: cover` with a sensible focal point, and make sure it still looks right at phone width (375 px).
- **Weight:** resize and compress to about 1600–1920 px wide, WebP (with a JPEG fallback only if you think it is needed), **≤ 250 KB each**. Show the navy background colour while the image loads, so the header never flashes white.

---

## 4. Verification

1. `.\.venv\Scripts\python.exe -m pytest`: report the real results. All existing tests must pass, with only the name-string expectations updated.
2. Stop any running server, start one fresh with `.\.venv\Scripts\python.exe app.py --no-browser`, and in the browser check all four pages at desktop width and at 375 px:
   - the new name appears in every header and tab title,
   - each page shows its own header image, with readable text over it,
   - no text was added, removed or changed apart from the name (compare the page text before and after, e.g. with `get_page_text` or a small script that diffs the visible text with the name normalized),
   - controls, sliders, Show/Update results, the Measurements filters and charts, and the 3D Simulator all still work, with no console errors,
   - approximation/extrapolation notices and value-type tags are still clearly distinguishable.
3. Take a screenshot of each page's header area and include them in the final report.

## 5. Final report

1. Files changed.
2. Remaining `atrophy armour` hits and why they stay.
3. Palette tokens and contrast ratios.
4. Font family, weights, licence and size.
5. The four header images: source, licence, final size.
6. Test results, browser checks and screenshots, and anything you could not verify.
