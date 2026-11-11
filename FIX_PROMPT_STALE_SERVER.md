# Fix: Scenario Explorer shows "Not found." on load until "Show results" is pressed

## Symptom
Opening http://127.0.0.1:8501 shows Step 1 · Scenario with only a red "Not found." box and no controls. After pressing "Show results", the controls appear and can be edited, but the "Not found." box stays.

Expected: all five inputs, the study filter and the duration slider render and are editable immediately on page load, before any results are requested.

## Diagnosis already done (verify, don't redo from scratch)
- `web/assets/js/explorer.js` loads the controls on page load from `GET /api/scenario/controls`. `server.py` defines that route in `_GET_ROUTES`, and an unknown `/api/` path returns `{"error": "Not found."}` (server.py ~line 91).
- A fresh server built from the current code answers `/api/scenario/controls` with **200**. The code on disk is correct.
- But **two `python.exe` processes were LISTENING on 127.0.0.1:8501 at the same time** (`netstat -ano`). The one answering requests was an **older server started before `/api/scenario/controls` existed**: it returned 404 for `/api/scenario/controls` and 200 for `/api/scenario`. That is why the page worked only after "Show results".
- Root cause of the double bind: `AtrophyServer` subclasses `ThreadingHTTPServer`, which sets `allow_reuse_address = True`. On Windows that maps to `SO_REUSEADDR`, which lets a second process bind the same port without an error, so a stale server silently keeps serving old code.

## Tasks
1. **Prevent silent double-binding.** In `server.py`, make the server refuse to start when the port is already in use. On Windows, set `allow_reuse_address = False` and use `SO_EXCLUSIVEADDRUSE` (guard it with `hasattr(socket, "SO_EXCLUSIVEADDRUSE")`). Keep the current behaviour on other OSes. Make sure `app.py` then prints a clear message, e.g. "Port 8501 is already in use, probably by an older Atrophy Armour server. Close that terminal/process or start with --port 8502", and exits with a non-zero code.
2. **Make the page robust on first load.** In `explorer.js`, render the controls as soon as `/api/scenario/controls` succeeds, with no dependency on "Show results". If the controls request fails, show a helpful message (the HTTP status, and for 404 "The running server looks out of date — restart it with `.\.venv\Scripts\python.exe app.py`") instead of a bare "Not found.". Clear any old error box once a later request succeeds.
3. **Detect version skew.** Add a lightweight `GET /api/health` (or include it in the existing payloads) returning an app/API version string. If the page and the server disagree, show a one-line "server is outdated, restart it" notice.
4. **Tests:** 
   - a server test that starting a second server on an occupied port raises a clear error (at minimum on Windows),
   - a test that `/api/scenario/controls` returns 200 with the controls payload and needs no prior `/api/scenario` call,
   - a test for `/api/health` if you add it.
   Run `.\.venv\Scripts\python.exe -m pytest` and report the real results.
5. **Manual check:** stop every running server, start one fresh, and load `/` and `/index.html` in the browser with a hard refresh (Ctrl+F5). Confirm the controls are editable before pressing anything, that changing controls doesn't throw console errors, and that "Show results" still works. Then start a second instance on the same port and confirm it refuses with the clear message.
6. Add a short "Troubleshooting" note to `README.md`: how to run without activating the venv (`.\.venv\Scripts\python.exe app.py`), and what to do if a port is already in use.

Don't change any scientific logic, evidence data, or the other pages.
