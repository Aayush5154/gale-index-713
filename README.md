# Wind Forecast Analytics

**Repository handle:** `gale-index-713`  
**Live app:** <https://windforecast5154.vercel.app>  
**Live API:** <https://wind-forecast-e9oq.onrender.com/docs>  
**Status:** deployed MVP. Live Elexon access, backend tests, frontend build/lint, Lighthouse audits, the Docker Compose runtime, and a public Vercel + Render deployment were executed.

A full-stack analytics prototype for GB electricity procurement teams who need to audit national wind forecasts at the moment a day-ahead decision had to be made. It joins decision-time WINDFOR forecasts to FUELHH wind outturn, exposes the exact publication used for every delivery hour, and reports retrospective error without hiding missing data.

The application deliberately does **not** cover weather modelling, demand, prices, generation mix, procurement volumes, financial savings, or half-hourly forecast fabrication. All generation values are MW as supplied by Elexon.

---

## 1. Overview

The tool answers two separate questions:

1. **Was a forecast available when the decision was made?** This is forecast coverage at the cut-off, not accuracy.
2. **How far was the selected forecast from the eventual outturn?** This is retrospective error against FUELHH WIND.

The default analysis window is delivery on **1–31 January 2026**, with a **09:20 Europe/London D-1** decision cut-off. Both the window and the cut-off are configurable in the UI and API. The default is a documented modelling choice, not a claim about a client's only procurement deadline.

Two source modes are supported:

- `live`: query the public Elexon Insights Solution API on demand.
- `fixture`: serve a labelled synthetic January 2026 dataset for offline demos and deterministic edge-case review.

---

## 2. Key features

- Decision-time forecast selection: only publications with `publishTime <= cutoff`; the latest eligible publication wins.
- Per-delivery-day cut-offs, or one fixed cut-off for the whole window.
- Exact hourly join between hourly WINDFOR forecasts and half-hourly FUELHH outturn.
- MAE, RMSE, MBE, MAPE, max absolute error, daily MAE, coverage, and signed-error histogram.
- Missing-forecast inspection with publication and cut-off audit fields.
- Explicit MAPE zero/near-zero handling and excluded-pair counts.
- No future-forecast leakage, interpolation, substitution, scaling, or bias correction.
- Four responsive views: Overview, Forecast Explorer, Accuracy Analysis, and Methodology & Data Quality.
- Loading skeletons, empty states, retryable errors, accessible focus styles, and fixture-data labelling.
- Bounded in-memory cache, request coalescing, HTTP timeouts/retries, and sanitised API errors.
- Docker Compose, Vercel, Render, and Heroku configuration files.

---

## 3. Architecture

```text
Browser (React + TypeScript + Vite + Tailwind + Recharts)
        |
        |  /api  (same-origin through nginx in Docker; Vite proxy in dev)
        v
FastAPI application
  routes -> analysis orchestration -> forecast selection
                                  -> hourly comparison
                                  -> metrics / daily / histogram
        |
        +--> Elexon client (chunked requests, retries, bounded TTL cache)
        |        -> FUELHH WIND stream
        |        -> WINDFOR stream
        |
        +--> Fixture client (synthetic JSON, explicit is_synthetic flag)
```

The backend is stateless apart from a bounded in-process cache. There is no database, user account system, or persistence layer. The frontend calls only the analytics API; it never calls Elexon directly.

Pandas is used to group comparison rows by their Europe/London delivery date, including DST transition days, before the shared coverage and accuracy functions calculate each daily record. The business logic is outside the route handlers. Routes resolve and validate the query, then delegate to services under `backend/app/services/`.

---

## 4. Data sources

Base URL verified against the public API:

```text
https://data.elexon.co.uk/bmrs/api/v1
```

| Dataset | Endpoint | Native resolution | Query constraint |
|---|---|---|---|
| FUELHH | `/datasets/FUELHH/stream` | Half-hourly average MW | Date-range request capped at 7 days; filtered to `fuelType=WIND` |
| WINDFOR | `/datasets/WINDFOR/stream` | Hourly MW | Publication-time range capped at 7 days; no delivery-date filter |

Observed live characteristics in January 2026:

- FUELHH WIND values are half-hourly **average MW**.
- WINDFOR publications contained 73 hourly delivery values.
- Eight publications per day were observed at approximately 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, and 22:30 UTC. This is an observed pattern, not a guaranteed schedule.
- The backend fetches in six-day chunks (below the seven-day upstream cap), with bounded concurrency and retries.
- Because WINDFOR has no delivery-date filter, the backend derives a conservative publication window from the first and last decision cut-offs and filters the returned records again.

`https://bmrs.elexon.co.uk/api-documentation/guidance` is the public guidance entry point. Elexon's documentation pages are not treated as data endpoints.

---

## 5. Decision cut-off

A forecast is eligible only if it existed at the decision time. The cut-off is part of the query, not a display detail.

**Default:** 09:20 Europe/London on D-1, based on the EPEX SPOT GB 60-minute day-ahead auction gate closure.

The default is configurable in the UI and through `cutoff_time` / `cutoff_datetime`. Documented alternatives include:

- N2EX day-ahead gate closure at 09:50 London.
- GB 30-minute day-ahead auction at 15:30 London.

These are modelling alternatives, not assertions about a specific client's contractual deadline.

### Daily D-1 mode

For each delivery day `D`, resolve the configured local time on `D-1`. Delivery days may therefore use different forecast publications. This mirrors a repeated day-ahead decision process and is the default.

### Fixed timestamp mode

A single cut-off applies to every interval. It must precede the first delivery interval; otherwise the API rejects the query. This supports audits of a specific historical decision or a non-standard gate closure.

### Decision-date ambiguity

“January 2026 decisions” is not the same as “delivery in January 2026.” Delivery on 1 January uses a cut-off on 31 December 2025. The default delivery window of 1–31 January therefore includes decisions made from 31 December through 30 January. If the requirement is decisions made during January, include delivery through 1 February so the 31 January cut-off is represented.

The application does not infer which definition is intended. The selected delivery window and cut-off are shown explicitly in the UI and returned in API responses.

Cut-offs are resolved in Europe/London and stored internally as UTC. The UTC offset changes across daylight-saving transitions, so the expected interval count follows the real London-day length: 23 or 25 hours on transition days.

---

## 6. Forecast selection

For every hourly delivery interval, the backend performs the same deterministic sequence:

1. Normalise the WINDFOR delivery start to UTC and consider only records whose `startTime` exactly equals the hourly delivery timestamp.
2. Keep records whose `publishTime` is at or before the decision cut-off and strictly before the delivery hour.
3. Select the latest `publishTime` among eligible records.
4. If multiple eligible records share the winning `publishTime`, select the highest generation value deterministically and flag the interval as a duplicate-publication tie.
5. If no eligible record exists, mark the interval `missing_forecast` and count it in coverage.
6. Record the selected publication, cut-off, lead time, eligible version count, and previous eligible publication for auditability.

A record published after the cut-off is never used, even if it is closer to delivery. A missing forecast is never filled by a later publication, a prior day's value, or an interpolated value.

The Forecast Explorer's detail panel exposes the selected publication and the half-hours that produced the hourly outturn.

---

## 7. Matching, resolution, and units

WINDFOR is hourly; FUELHH WIND is half-hourly. The comparison is deliberately hourly, at WINDFOR's native resolution.

For a delivery hour beginning at `HH:00`:

```text
hourly outturn = (FUELHH at HH:00 + FUELHH at HH:30) / 2
```

If either half-hour is missing or invalid, the hourly outturn is unavailable. The tool does **not** average a single reading, interpolate, or fall back to another source.

All values are MW as supplied. There is no MWh conversion and no multiplication by 0.5. Half-hourly outturn remains visible in the Forecast Explorer at its native timestamps.

Per-interval arithmetic:

```text
signed error   = forecast − outturn                 (MW)
absolute error = |forecast − outturn|               (MW)
squared error  = (forecast − outturn)^2             (MW²)
APE            = |forecast − outturn| / |outturn|   (only when |outturn| >= 1 MW)
```

Delivery timestamps are normalised to UTC for joins and calculations; London local timestamps are used for display and cut-off resolution.

---

## 8. Metrics

All metrics are calculated server-side from the same valid hourly pairs. Coverage is reported separately and is never labelled accuracy.

| Metric | Formula | Notes |
|---|---|---|
| MAE | `mean(abs(forecast - outturn))` | MW; valid pairs only |
| RMSE | `sqrt(mean((forecast - outturn)^2))` | MW; penalises large misses |
| MBE | `mean(forecast - outturn)` | MW; positive means overforecast |
| MAPE | `mean(abs(forecast - outturn) / abs(outturn)) * 100` | Only where `abs(outturn) >= 1 MW`; exclusions counted |
| Max absolute error | `max(abs(forecast - outturn))` | Includes the timestamp of the worst pair |
| Coverage | `eligible forecast hours / expected delivery hours * 100` | Availability at cut-off; not accuracy |
| Valid-pair percentage | `valid pairs / expected delivery hours * 100` | Both forecast and complete outturn present |
| Daily MAE | MAE grouped by London delivery date | Same pair rules |
| Histogram | Counts of signed error bins | Bin width returned by the API |

Zero/near-zero handling is explicit:

- The MAPE denominator floor is **1.0 MW** by default (`MAPE_MIN_ACTUAL_MW`).
- Pairs below the floor remain in MAE, RMSE, and MBE but are excluded from MAPE.
- The API returns `mape_valid_count` and `mape_excluded_count` so the exclusion is visible.
- MAPE is not presented as a substitute for MW-based error.

Expected intervals are calculated from the actual delivery timeline. A normal January day contributes 24 hourly intervals; DST transition days can contribute 23 or 25.

---

## 9. Data quality and failure handling

| Topic | Handling |
|---|---|
| Non-WIND actual rows | Dropped before selection |
| Invalid or non-finite generation values | Dropped and counted in data-quality metadata where applicable |
| Revised actual values | Latest publication wins; ties resolved deterministically and counted |
| Missing actual half-hour | Hourly outturn becomes unavailable; no interpolation |
| Missing forecast at cut-off | Marked `missing_forecast`; counted and exposed in the UI |
| Duplicate forecast publications | Latest publication wins; equal latest times resolved by highest generation and flagged |
| Forecast after cut-off | Never eligible |
| Forecast lead time over 48 h | Selected if eligible, flagged as stale |
| Empty dataset | Structured error or empty state; no fabricated values |
| Upstream timeout | Bounded connect/read timeout and retry, then sanitised `503` |
| HTTP 429 / 5xx | Bounded retries with backoff; `Retry-After` respected where parseable |
| Malformed JSON | Sanitised `502`; payload is not exposed to the user |
| Frontend request timeout | Aborts after 60 seconds and offers retry |
| Cache | Bounded TTL cache, request coalescing, no unbounded growth |

Warnings are returned by the API and displayed in the UI. Missing values remain missing; they are not hidden inside a zero.

---

## 10. API

Swagger UI: `http://localhost:8000/docs` when running the backend directly, or `http://localhost:8080/docs` through the Docker frontend proxy.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Application, dependency, and cache status |
| `GET` | `/api/metadata` | Datasets, defaults, cut-off rules, metric definitions, limitations |
| `GET` | `/api/forecasts` | Selected forecast versions per delivery hour |
| `GET` | `/api/comparison` | Hourly pairs, signed/absolute/squared errors, APE, half-hour outturn |
| `GET` | `/api/metrics` | Aggregate metrics, coverage, decision context, histogram, warnings |
| `GET` | `/api/accuracy/daily` | Daily metric breakdown |

Shared query parameters:

| Parameter | Meaning |
|---|---|
| `from_date` | First delivery date, `YYYY-MM-DD`, London calendar |
| `to_date` | Last delivery date, `YYYY-MM-DD` |
| `cutoff_mode` | `daily` or `fixed` |
| `cutoff_time` | `HH:MM`, Europe/London, used in daily mode |
| `cutoff_datetime` | Local ISO datetime for fixed mode; must precede the first interval |

The maximum range is 92 days by default (`MAX_RANGE_DAYS`). Invalid dates, reversed ranges, oversized windows, malformed times, or a fixed cut-off that does not precede delivery return HTTP `422`.

Example:

```bash
curl "http://localhost:8000/api/metrics?from_date=2026-01-01&to_date=2026-01-31&cutoff_mode=daily&cutoff_time=09%3A20"
```

Fixed-cut-off example:

```bash
curl "http://localhost:8000/api/comparison?from_date=2026-01-05&to_date=2026-01-05&cutoff_mode=fixed&cutoff_datetime=2026-01-04T09%3A20"
```

Error shape:

```json
{
  "error": {
    "code": "invalid_query",
    "message": "The end date must be on or after the start date.",
    "details": { "field": "to_date" },
    "request_id": "a1b2c3d4e5f6"
  }
}
```

Status codes include `422` for invalid queries, `502` for invalid upstream responses, `503` when Elexon is unavailable, and sanitised `500` for unexpected failures. Stack traces are logged server-side but never returned to API clients.

---

## 11. Frontend pages

| Route | Page | Contents |
|---|---|---|
| `/overview` | Wind Forecast Analytics | Coverage, MAE, RMSE, MBE, decision context, data source/freshness, warnings, integrity counts |
| `/explorer` | Forecast Explorer | Forecast/outturn chart, publication and cut-off audit fields, filterable table, missing-forecast inspection |
| `/accuracy` | Accuracy Analysis | Metric definitions, daily MAE/coverage chart, signed-error histogram, daily table, low-coverage warning |
| `/methodology` | Methodology & Data Quality | Sources, cut-off rules, selection algorithm, resolution/units, metric definitions, quality rules, limitations, API notes |

UI details:

- URL state carries `from`, `to`, `mode`, `cutoff`, and `at`, so views are shareable across pages.
- Daily mode and fixed mode are both available in the filter bar.
- Invalid local filters are blocked before navigation; the API also validates them independently.
- Charts show explicit empty states rather than blank axes or `NaN`.
- Coverage is visually separated from accuracy and repeated warnings explain that coverage is availability.
- The synthetic fixture banner is persistent whenever `is_synthetic=true`.
- CSV export writes the filtered explorer rows, including publication, cut-off, lead time, and APE.
- Keyboard focus rings, a skip link, native control semantics, and `role="img"` chart labels are included.
- The theme is a near-black canvas with warm off-white type and one yellow accent; orange is reserved for caution states and red for errors. There are no gradients, glass effects, fake logos, or emojis.

No frontend unit test suite is included. The production build, TypeScript compiler, ESLint, and browser smoke checks were run; see section 16.

---

## 12. Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── fixtures/
│   ├── scripts/
│   ├── tests/
│   ├── Dockerfile
│   ├── Procfile
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vercel.json
│   └── vite.config.ts
├── .env.example
├── docker-compose.yml
├── render.yaml
└── VIDEO_DEMO_SCRIPT.md
```

---

## 13. Local development

Prerequisites: Python 3.12, Node.js 22+, npm 10+.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edit DATA_MODE=live or DATA_MODE=fixture as required.
uvicorn app.main:app --reload --port 8000
```

macOS/Linux equivalent:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The backend exposes Swagger at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`.

Production check:

```bash
npm run build
npm run preview
```

`npm run preview` runs on port `4173` and proxies `/api` to the local backend.

---

## 14. Configuration

The backend reads environment variables through Pydantic Settings. The frontend reads `VITE_API_BASE_URL` at build time. No secrets are required.

| Variable | Default | Purpose |
|---|---|---|
| `DATA_MODE` | `live` | `live` or `fixture` |
| `ENVIRONMENT` | `development` | Environment label returned by metadata/health |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Upstream API base |
| `ELEXON_TIMEOUT_SECONDS` | `45` | HTTP read timeout |
| `ELEXON_CONNECT_TIMEOUT_SECONDS` | `10` | HTTP connect timeout |
| `ELEXON_MAX_RETRIES` | `2` | Retry attempts for 429/5xx/transport errors |
| `ELEXON_CONCURRENCY` | `4` | Concurrent chunk requests |
| `ELEXON_CHUNK_DAYS` | `6` | Days per upstream request (max 7) |
| `ELEXON_FORECAST_LOOKBACK_DAYS` | `3` | Publication lookback before the first cut-off |
| `CACHE_TTL_SECONDS` | `900` | In-memory cache TTL |
| `CACHE_MAX_ENTRIES` | `128` | Bounded cache size |
| `PREWARM_DEFAULT_RANGE` | `true` | Warm the default January range on startup |
| `MARKET_TIMEZONE` | `Europe/London` | Local market time zone |
| `DEFAULT_FROM_DATE` | `2026-01-01` | Default delivery start |
| `DEFAULT_TO_DATE` | `2026-01-31` | Default delivery end |
| `DEFAULT_CUTOFF_TIME` | `09:20` | Default daily cut-off |
| `MAX_RANGE_DAYS` | `92` | Maximum query range |
| `MAPE_MIN_ACTUAL_MW` | `1.0` | Denominator floor for MAPE |
| `STALE_FORECAST_HOURS` | `48` | Lead-time flag threshold |
| `FRONTEND_ORIGINS` | localhost origins | Comma-separated CORS allowlist |
| `FIXTURE_DIR` | `backend/fixtures` | Fixture directory override |
| `VITE_API_BASE_URL` | `/api` | Frontend API base at build time |

See `backend/.env.example`, `frontend/.env.example`, and root `.env.example`.

---

## 15. Fixture mode

Fixture mode is for offline demonstration and deterministic data-quality review, not for real analysis.

```powershell
$env:DATA_MODE = "fixture"
uvicorn app.main:app --reload --port 8000
```

The fixtures are generated by:

```bash
cd backend
python scripts/generate_fixtures.py
```

They intentionally include:

- a non-WIND actual row,
- an invalid generation value,
- a revised actual value,
- two missing actual half-hours,
- one missing forecast hour,
- a duplicate forecast publication,
- zero and near-zero actual values for MAPE handling.

Every fixture response carries `is_synthetic=true`, and the UI displays a persistent warning. Fixture values are synthetic and must not be used for procurement decisions.

Fixture January 2026 summary: 743/744 hourly forecasts were available, 741 valid pairs were formed, 2 actual half-hour gaps were preserved, 1 forecast was missing, 2 MAPE pairs were excluded, and a duplicate publication tie was flagged.

---

## 16. Tests and checks

### Backend

```powershell
cd backend
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check app tests
.\.venv\Scripts\python -m compileall -q app
```

Verified results:

```text
83 passed
All checks passed!
compileall: ok
```

The pytest suite covers WIND filtering, timestamp normalisation, cutoff eligibility, latest-publication selection, post-cutoff rejection, missing forecasts, duplicate resolution, actual aggregation, matching, every metric, zero actuals, empty datasets, invalid numerics, API error behaviour, retries/chunking, and fixture edge cases. Upstream HTTP is mocked; the tests do not call Elexon.

### Frontend

```powershell
cd frontend
npm run build
npm run lint
npm run typecheck
```

Verified:

- TypeScript build and Vite production build succeed.
- ESLint completes with zero warnings under `--max-warnings=0`.
- The production preview was loaded in a browser; direct SPA routes, the `/api` proxy, charts, table pagination, filters, fixed cut-off validation, error/retry, and CSV download worked.

The local Python test venv is 3.11.3; the Docker backend image is Python 3.12 with the pinned requirements and passed the runtime smoke checks.

Bundle split after production build:

```text
index    ~108 kB
react    ~166 kB
charts   ~418 kB
```

These are raw minified sizes from the local build, not performance guarantees.

### Lighthouse audit

A Lighthouse desktop-preset audit of the local production preview returned **100** for performance, accessibility, best practices, and SEO on Overview, Forecast Explorer, and Accuracy Analysis. The mobile-preset Overview run returned 96 for performance and **100** for accessibility, best practices, and SEO. The initial contrast finding on Forecast Explorer was fixed by raising the muted-label colour contrast, then re-audited. Lighthouse is automated and does not replace manual screen-reader or keyboard testing.

### Docker build and runtime

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Both images built successfully. The backend and frontend containers reached `healthy`, the nginx `/api` proxy returned live Elexon data, Swagger loaded through `/docs`, and the backend process ran as UID/GID `10001` rather than root. A browser smoke test at `http://127.0.0.1:8080/overview` showed 744/744 coverage and MAE 2,142 MW, and `/explorer` rendered 744 table rows with no chart errors. See section 18.

### Not tested

- No frontend unit/component test framework is configured.
- No manual screen-reader or keyboard-only audit was completed.
- No load or penetration test was run.
- The public deployment was smoke-tested for health, CORS, and page load; it has not been load-tested.

---

## 17. Verified results

### Live Elexon, full January 2026

Executed against the live API on 27 October 2026 with delivery `2026-01-01` to `2026-01-31`, daily cut-off `09:20` Europe/London.

| Measure | Result |
|---|---|
| Expected delivery hours | 744 |
| Forecasts available at cut-off | 744 (100.0%) |
| Valid forecast/outturn pairs | 744 |
| Missing forecasts | 0 |
| Missing outturn hours | 0 |
| MAE | 2,142.1203 MW |
| RMSE | 2,611.6951 MW |
| MBE | +1,851.9039 MW |
| MAPE | 22.3784% (744 valid, 0 excluded) |
| Maximum absolute error | 6,870 MW at `2026-01-12T01:00Z` |
| Upstream records inspected | 1,488 FUELHH · 19,272 WINDFOR |
| Upstream chunks | 6 FUELHH + 6 WINDFOR |

The persistent positive MBE (roughly 1.85 GW) indicates that selected WINDFOR values were above FUELHH WIND outturn across this month. That can reflect forecast error, different wind-farm populations visible to NESO versus transmission-connected FUELHH, or both. The application applies **no adjustment** and discloses the bias rather than calibrating it away.

Indicative local latency was about 2 seconds for the first full-month request and about 0.2–0.5 seconds for cached requests. These figures are environmental observations, not service-level guarantees.

Elexon data can be revised. Re-running the same query later may produce slightly different outturn values and metrics.

### Fixture mode

The synthetic January 2026 dataset exercised missing values, duplicate publications, zero/near-zero actuals, and incomplete hourly outturn. The UI displayed the fixture warning and the API returned `is_synthetic=true`. Results are intentionally not presented as real market outcomes.

---

## 18. Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Then:

- Frontend: `http://localhost:8080`
- Swagger through nginx: `http://localhost:8080/docs`
- Backend direct: `http://localhost:8000`
- Stop the stack: `docker compose down`

To run the deterministic synthetic demo instead:

```powershell
$env:DATA_MODE = "fixture"
docker compose up --build -d
```

or set `DATA_MODE=fixture` in the root `.env`. Rebuild or recreate after changing `DATA_MODE` so the environment reaches the backend container.

What is provided:

- Multi-stage frontend build, served by nginx.
- nginx same-origin `/api` proxy to the backend and SPA fallback.
- Backend image running as a non-root user, with a health check.
- Compose health dependency from frontend to backend.
- Security headers and gzip in nginx.

**Verified on 28 October 2026:** `docker compose config --quiet` passed, both images built, and `docker compose ps` showed `grid2-backend-1` and `grid2-frontend-1` as `healthy`. Through nginx, `/api/health` returned `status=ok`, `data_mode=live`, and an `ok` Elexon dependency; `/docs` served Swagger; `/overview` and `/explorer` loaded live data. The backend container ran as `uid=10001(appuser) gid=10001(appuser)`. This validates the stack on Docker Desktop for Windows with Linux containers.

The containers used the project defaults and a live Elexon connection. No Docker secrets are required.

---

## 19. Deployment

The MVP is deployed publicly on the free tiers of Vercel (frontend) and Render (backend):

| Component | URL | Platform |
|---|---|---|
| Web app | <https://windforecast5154.vercel.app> | Vercel, project root `frontend` |
| API base | <https://wind-forecast-e9oq.onrender.com/api> | Render web service, root `backend` |
| Swagger UI | <https://wind-forecast-e9oq.onrender.com/docs> | Render |
| Health check | <https://wind-forecast-e9oq.onrender.com/api/health> | Render |

Verified on 28 October 2026: the health check reports `status: ok`, `data_mode: live`, `is_synthetic: false`, and a healthy Elexon dependency; CORS returns `access-control-allow-origin: https://windforecast5154.vercel.app`; the frontend returns HTTP 200.

Active production configuration:

```text
# Render
DATA_MODE=live
ENVIRONMENT=production
FRONTEND_ORIGINS=https://windforecast5154.vercel.app

# Vercel (build time)
VITE_API_BASE_URL=https://wind-forecast-e9oq.onrender.com/api
```

Render's free instance spins down after inactivity, so the first request after an idle period can take 30–60 seconds. The API is stateless apart from its in-process TTL cache; there is no database to provision.

### Frontend: Vercel

1. Import the repository into Vercel.
2. Set the project root to `frontend`.
3. Framework preset: Vite.
4. Build command: `npm run build`.
5. Output directory: `dist`.
6. Add environment variable `VITE_API_BASE_URL=https://<your-render-or-heroku-api>/api`.
7. Deploy. `frontend/vercel.json` provides SPA rewrites and basic security headers.

The frontend must use the absolute backend URL on Vercel; it does not proxy `/api` itself. `VITE_API_BASE_URL` is inlined at build time, so changing it requires a redeploy.

### Backend: Render

The repository contains `render.yaml`, a Render Blueprint for the backend:

- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips "*"`
- Health check: `/api/health`
- Plan: `free`
- Default mode: `live`

The running service was created with the equivalent manual Web Service settings. After creating the service, set:

```text
FRONTEND_ORIGINS=https://<your-vercel-app>.vercel.app
```

Optionally set `DATA_MODE=fixture` for a demo environment. Then point the Vercel `VITE_API_BASE_URL` at the Render service URL plus `/api`.

### Backend: Heroku

The `backend/Procfile` and `backend/runtime.txt` are provided.

```bash
heroku create <unique-app-name>
heroku config:set DATA_MODE=live ENVIRONMENT=production FRONTEND_ORIGINS=https://<your-vercel-app>.vercel.app
git subtree push --prefix backend heroku main
```

Alternatively, deploy only the `backend/` directory. Heroku's `$PORT` is respected by the Procfile command.

The Render deployment is live and verified (see the table above). The Heroku configuration files are supplied but were not exercised against that platform; treat the exact runtime versions and plan behaviour as unverified until deployed.

### CORS

The backend allows the comma-separated `FRONTEND_ORIGINS` allowlist. The Docker frontend is same-origin through nginx and does not need CORS. Direct browser calls from Vercel/Heroku development origins do.

---

## 20. Security and reliability

- No API keys or secrets are required or embedded; `.env` files are ignored.
- CORS is restricted to configured origins.
- All endpoints are read-only `GET`s; there is no mutation surface.
- Upstream requests have connect/read timeouts, bounded retries, and `Retry-After` handling.
- Malformed upstream JSON, HTTP errors, and empty payloads are converted to sanitised application errors.
- Request IDs are attached to error responses for correlation.
- Stack traces are not returned to browser clients.
- Response schemas are validated with Pydantic.
- The cache is bounded by entry count and TTL; concurrent identical requests are coalesced.
- The backend Docker image runs as a non-root user.
- nginx sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a restrictive `Permissions-Policy`.
- The frontend displays API errors without exposing raw upstream bodies.

This is a public analytics prototype, not a hardened multi-tenant service. There is no authentication, authorisation, rate limiting at the edge, audit trail, or persistence. Add those before exposing sensitive operational workflows.

---

## 21. Limitations and interpretation

- **Resolution mismatch:** WINDFOR is hourly, FUELHH is half-hourly. The comparison is hourly by design; no half-hourly forecast is fabricated.
- **Population mismatch:** NESO's forecast may cover a different wind-farm population than transmission-connected FUELHH WIND. The observed positive bias is disclosed, not “fixed.”
- **Cut-off assumptions:** 09:20 London is a documented default modelling choice. A client's actual gate closure may differ; use the configurable time or fixed mode.
- **Decision-date ambiguity:** delivery window and decision window are not the same thing; both must be stated explicitly.
- **Data revisions:** Elexon can revise FUELHH outturn. Results are not immutable snapshots.
- **MAPE:** percentage errors are unstable near zero; the 1 MW floor and exclusions are reported.
- **No financial analysis:** no prices, procurement volumes, imbalance costs, or savings are modelled.
- **No weather or demand modelling:** the tool evaluates forecast error; it does not explain or improve the forecast.
- **No persistence:** cache entries disappear on restart and are process-local.
- **Single-process cache:** multiple workers would not share cache state. The supplied start commands use one worker.
- **Coverage is not accuracy:** a fully covered window can still have large errors, and a low-coverage window's metrics may be unrepresentative.

---

## 22. AI disclosure and verification status

This implementation was produced with substantial AI coding-assistant support using OpenCode and DeepSeek V4.1 Flash Free. The assistant wrote code, ran tests/builds, inspected the live Elexon API, and performed browser smoke checks. Findings were reported honestly, including mistakes found during review (for example, an APE display bug that was corrected and rechecked).

Verified in this environment:

- Live Elexon FUELHH and WINDFOR access, including a full January 2026 query.
- 83 backend tests passing.
- Ruff and Python compile checks passing.
- Frontend TypeScript production build and ESLint passing.
- Production preview, SPA routes, charts, filters, fixed mode, error/retry, and CSV export working in a browser.
- Lighthouse accessibility, best-practices, and SEO scores of 100 on Overview, Forecast Explorer, and Accuracy Analysis.
- Docker Compose images built, both containers healthy, nginx proxy and Swagger working, and the backend running as a non-root user.

Not verified:

- Vercel, Render, or Heroku deployment.
- Any live deployment URL.
- Platform-specific runtime/version behaviour for Render and Heroku.
- Manual assistive-technology testing, load testing, or security testing.

No API data, deployment URL, or test result in this document is fabricated. Synthetic fixture values are explicitly labelled. Real Elexon values are cited from actual live queries, with the caveat that upstream data can be revised.

---

## License

MIT. See `LICENSE`. The suggested anonymous repository handle is `gale-index-713`.
