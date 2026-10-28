# Video Demo Script

Two five-minute recordings: one for a client audience, one for a technical audience. The scripts are deliberately honest about what is and is not verified. Do not present the fixture dataset as Elexon data, and do not claim a cloud deployment or deployment URL that was not performed.

## Recording setup

Use a clean browser window at 1440×900 or 1280×800. Close unrelated tabs and notifications.

### Option A: deterministic fixture demo

```powershell
# Terminal 1
cd backend
$env:DATA_MODE = "fixture"
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173/overview`.

The persistent “Fixture mode” banner and `SYNTHETIC FIXTURE` badge must remain visible. Say clearly that values are synthetic and for demonstration only.

### Option B: live Elexon demo

```powershell
# Terminal 1
cd backend
$env:DATA_MODE = "live"
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173/overview`.

Use live mode if the network is stable. Say that Elexon data can be revised and that the first request may take a moment. Do not show stale or cached values as if they were a live snapshot without saying so.

### Before recording

- Confirm `/api/health` is `ok`.
- Confirm the page is not still loading.
- Have the default January 2026 window selected.
- Keep the browser console closed.
- Do not open a terminal showing secrets; there are none in the project.

---

# Part 1 — Client walkthrough (5:00)

**Audience:** procurement, analytics, and commercial stakeholders.  
**Goal:** explain the decision problem, the audit trail, and the limits.

## 0:00–0:30 — Opening

**Screen:** Overview at the top.

**Say:**

> This is a decision-time wind forecast analytics prototype for GB electricity procurement. It answers two questions: was a wind forecast available when the day-ahead decision had to be made, and how far was that forecast from Elexon’s eventual wind outturn?
>
> The default window is delivery in January 2026 with a 09:20 London cut-off on the day before delivery. The cut-off is configurable. The tool does not model prices, procurement volumes, or savings.

## 0:30–1:20 — Overview KPIs

**Screen:** Four KPI cards and the decision-context panel.

**Say:**

> The first number is coverage, not accuracy: 744 of 744 expected delivery hours had an eligible WINDFOR publication at the cut-off.
>
> MAE is the average absolute hourly miss in MW. RMSE penalises larger misses more heavily. MBE is signed, so a positive value means the forecast was above outturn on average. Here MBE is positive, which is a material observation; the tool discloses it and does not shift the data to make the chart look better.
>
> The decision-context panel shows the exact rule, the first and last cut-offs, the publication range, and the lead time. This is the audit trail.

**Point at:** “Coverage is availability, not accuracy” footnote.

## 1:20–2:00 — Change the decision window

**Screen:** Analysis window filter bar.

**Do:**

1. Point at “Daily D-1” and the 09:20 London cut-off.
2. Switch briefly to “Fixed cut-off”.
3. Show the fixed timestamp field and validation message if the timestamp is after the first delivery hour.
4. Switch back to Daily D-1.
5. Press Apply with a short date range, for example 1–2 January 2026.

**Say:**

> Daily mode asks a different question for each delivery day: what was published by 09:20 on the previous day? Fixed mode applies one timestamp to every interval and must precede the first delivery hour. Both are deliberate modelling choices. The selected window and cut-off are carried in the URL, so a colleague can reproduce the view.

## 2:00–3:05 — Forecast Explorer

**Screen:** `/explorer`, default January 2026.

**Do:**

1. Show the forecast/outturn chart.
2. Hover one hourly point and one :30 point.
3. Scroll to the table.
4. Open a row with “Details”.
5. Point out publication time, cut-off, lead time, eligible versions, and the two FUELHH half-hours.

**Say:**

> The yellow line is the selected hourly WINDFOR publication. The grey line is FUELHH WIND outturn at its native half-hourly resolution. At the half-hours we show only outturn; no half-hourly forecast is invented.
>
> Each table row records the exact publication used. The outturn is the arithmetic mean of the two half-hours. If either half-hour is missing, the hour is unavailable and remains visibly missing.
>
> The detail panel is the audit view: cut-off, selected publication, previous eligible publication, lead time, signed error, absolute error, squared error, and APE where the denominator is valid.

**Optional:** Click the “No forecast” status filter. If the selected window has none, switch to a window containing the fixture’s missing forecast; otherwise say the filter is available for missing-forecast inspection.

## 3:05–4:05 — Accuracy Analysis

**Screen:** `/accuracy`.

**Do:**

1. Show MAE, RMSE, MBE, MAPE, and largest miss.
2. Show the daily MAE/coverage chart.
3. Show the signed-error histogram.
4. Point at the daily table.

**Say:**

> Accuracy is retrospective and conditional on the pairs that exist. MAPE excludes outturn below 1 MW; the excluded count is visible. The daily chart puts MAE and coverage side by side, so a low-coverage day is not mistaken for a good day.
>
> The histogram shows the direction of error, not just its size. The concentration on the positive side is consistent with the positive MBE. The tool reports that; it does not calibrate or hide it.
>
> Coverage is not an accuracy score. A window with low coverage can produce misleading metrics, which is why the warning is explicit.

## 4:05–4:45 — Methodology and limits

**Screen:** `/methodology`, scroll through Scope, Sources, Cut-off, Selection, Matching, Metrics, Data Quality, Limitations.

**Say:**

> The methodology page records the source endpoints, the exact selection algorithm, the hourly matching rule, the metric formulas, and the quality controls.
>
> Two limitations matter commercially. WINDFOR is hourly while FUELHH is half-hourly, so the comparison is hourly by design. And the observed positive bias may reflect both forecast error and a difference in the wind-farm population visible to NESO versus transmission-connected FUELHH. This prototype does not adjust for that.
>
> The default 09:20 gate closure is configurable; it is not a claim about a specific contract.

## 4:45–5:00 — Close

**Screen:** Overview, top.

**Say:**

> This is an auditable forecast-error tool, not a trading or savings model. The next step would be to confirm the client’s actual gate closure and decision-date convention, then run the same selection rules against their procurement calendar.

**Do not say:** “This proves savings” or “This is deployed.” Neither is claimed by the verified project state.

---

# Part 2 — Technical walkthrough (5:00)

**Audience:** engineering, data, and architecture reviewers.  
**Goal:** show the pipeline, selection guarantees, and verification status.

## 0:00–0:30 — Stack and architecture

**Screen:** `README.md` architecture section, or a simple diagram.

**Say:**

> The frontend is React 18, TypeScript, Vite, Tailwind, Recharts, and Lucide. The backend is Python 3.12, FastAPI, Pydantic, HTTPX, and Pandas. The frontend calls only the backend; it never calls Elexon directly.
>
> The FastAPI routes validate the query and delegate to services for selection, hourly comparison, metrics, and daily aggregation. There is no database; there is a bounded in-process TTL cache.

## 0:30–1:15 — Elexon client and resilience

**Screen:** `backend/app/services/elexon_client.py`.

**Say:**

> Both datasets are fetched in six-day chunks, below Elexon’s seven-day request cap. The client uses bounded concurrency and retries for transport errors, 429s, and 5xx responses, including `Retry-After` where parseable.
>
> WINDFOR has no delivery-date filter, so the backend derives a publication window from the cut-offs, fetches it, then filters again during normalization.
>
> Responses are validated before use. Malformed JSON becomes a sanitised 502; upstream failure becomes a sanitised 503. JSON caching is bounded by TTL and entry count, and identical in-flight requests are coalesced.

## 1:15–2:15 — Decision-time selection

**Screen:** `backend/app/services/forecast_selection.py`, or the Methodology selection section.

**Say:**

> For each delivery hour, the selector filters to the exact normalised delivery timestamp and to publications at or before the applicable cut-off. It selects the latest eligible publish time.
>
> If two eligible values share the winning publication time, the higher generation value is selected deterministically and the row is flagged. If no eligible value exists, the hour is marked missing and counted. There is no fallback to a later publication.
>
> Daily mode resolves a cut-off per delivery day. Fixed mode applies one timestamp and rejects a cut-off after the first interval. This prevents future-forecast leakage and makes the selected version auditable.

## 2:15–3:00 — Matching and metrics

**Screen:** `backend/app/services/comparison.py` and `metrics.py`, or `/accuracy`.

**Say:**

> WINDFOR is hourly. FUELHH is half-hourly. For each hour, the outturn is the mean of the two half-hours only when both are present. There is no interpolation and no multiplication by 0.5.
>
> Metrics are MAE, RMSE, MBE, MAPE, max absolute error, and daily MAE. MAPE uses a 1 MW denominator floor and returns both included and excluded counts.
>
> Coverage is calculated separately from model error. The API never labels coverage as accuracy.

## 3:00–3:45 — API and contracts

**Screen:** `http://localhost:8000/docs` or `backend/app/api/routes.py`.

**Say:**

> There are six endpoints: health, metadata, forecasts, comparison, metrics, and daily accuracy. Query validation covers dates, range size, cut-off format, and fixed-cut-off ordering.
>
> Errors have a stable shape with a code, safe message, optional details, and request ID. Upstream failures map to 502 or 503; invalid queries map to 422. Stack traces are logged but not returned.

## 3:45–4:20 — Frontend behaviour

**Screen:** `/explorer` and `/accuracy`.

**Say:**

> URL state carries the window, mode, cut-off, and fixed timestamp, so views are shareable. The frontend has loading skeletons, empty states, retryable errors, and a fixture banner driven by metadata.
>
> Charts use explicit empty states instead of blank axes. The table has status filters, pagination, inline audit detail, and CSV export. Keyboard focus and semantic controls are in place; automated accessibility testing was not run.

## 4:20–4:45 — Verification

**Screen:** README “Tests and checks” and “Verified results”.

**Say:**

> The backend suite has 83 passing tests, typically in a few seconds on a local machine. Ruff and compile checks pass. The frontend production build and ESLint pass with zero warnings. The production preview was loaded in a browser; chart, table, filters, fixed mode, retry, and CSV were checked. Lighthouse scored the main pages at 100 for accessibility, best practices, and SEO after a contrast fix.
>
> A live full-January 2026 query returned 744 of 744 forecast hours, MAE 2,142.1203 MW, RMSE 2,611.6951 MW, and MBE +1,851.9039 MW. Elexon data can revise, so those are validation snapshots.

## 4:45–5:00 — Honest limits

**Screen:** README “Verification status”, or terminal showing `docker compose ps` with both containers healthy.

**Say:**

> The Docker Compose stack was built and both containers reached healthy. The nginx proxy served the SPA, `/api/health`, live Elexon data, and Swagger, and the backend ran as a non-root user. Vercel, Render, and Heroku were not deployed; there are no live cloud URLs in this repository.
>
> The deployment files are supplied, but platform runtime behaviour remains unverified. The application applies no bias correction, models no financial savings, and does not fabricate half-hourly forecasts.

**Do not say:** “Fully deployed” or “production-ready.” Those claims would be false for this repository state.

---

## Optional closing slide

- Data: Elexon Insights Solution, FUELHH WIND and WINDFOR.
- Resolution: hourly comparison; half-hourly outturn retained.
- Decision rule: latest eligible publication at the applicable cut-off.
- Verification: 83 backend tests; frontend build/lint; live January 2026 query.
- Verified: Docker Compose runtime, both containers healthy.
- Unverified: cloud deployment.
