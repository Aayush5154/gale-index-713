# Short Video Script (≈3 minutes)

**Live app:** https://windforecast5154.vercel.app
**Live API / Swagger:** https://wind-forecast-e9oq.onrender.com/docs

## Before recording

1. Open https://wind-forecast-e9oq.onrender.com/api/health in a tab and wait for `"status":"ok"` (the free instance sleeps, so this wakes it).
2. Close that tab. Open https://windforecast5154.vercel.app/overview at 1440×900 or 1280×800.
3. Use the default January 2026 window and 09:20 cut-off. Do not change data between takes.
4. Keep the browser console closed and notifications off.

## Narration

### 0:00–0:20 — What this is

**Screen:** Overview page, top.

> This is a wind forecast analytics dashboard for Great Britain's electricity grid. It answers one question: how accurate was the wind forecast that was actually available when a day-ahead decision had to be made? It uses live data from Elexon, the body that publishes official grid data.

### 0:20–0:45 — The four headline numbers

**Screen:** The four KPI cards.

**Do:** Point at each card in turn.

> At the top we have four numbers. Forecast coverage is how many hours actually had a forecast published before the cut-off — 744 of 744 here, so coverage is complete. This is availability, not accuracy.
>
> Mean absolute error is the average miss in megawatts. Root mean squared error punishes big misses more. Mean bias error is signed, so a positive number means the forecast was, on average, higher than what actually happened.

### 0:45–1:10 — The audit trail

**Screen:** Decision context panel, then Data source & freshness panel.

> Below that is the audit trail: the exact rule used, the first and last cut-off, the range of forecast publications used, and the lead time. Next to it, the data source panel confirms this is live Elexon data, not a test fixture, and shows when it was fetched and what is cached.

### 1:10–1:30 — Changing the question

**Screen:** Analysis window filter bar.

**Do:** Click `Fixed cut-off`, pause, then click `Daily D-1` again. Change the dates to 1–3 January 2026 and press `Apply`.

> I can change the delivery window and the cut-off. Daily D-1 means each delivery day is judged against 09:20 London time the day before. Fixed means one single timestamp for every hour. The settings are kept in the URL, so I can send this exact view to a colleague.

### 1:30–2:05 — Forecast Explorer

**Screen:** `Forecast Explorer`.

**Do:** Show the chart, hover one point, scroll to the table, click `Details` on a row.

> This page shows the detail. The yellow line is the hourly wind forecast that was chosen at the decision time. The grey line is the actual wind output, published every half hour. We only draw a forecast where one existed — we never invent half-hourly forecast values.
>
> The table lists every hour, and `Details` opens the evidence for that row: which forecast publication was used, the cut-off, the lead time, and the error. You can filter by status — for example, hours with no forecast — and download the rows as a CSV.

### 2:05–2:35 — Accuracy Analysis

**Screen:** `Accuracy Analysis`.

**Do:** Point at the MAPE card, the "Largest absolute miss" card, the daily bar chart, then the histogram.

> This page summarises the error. Alongside MAE and RMSE we show percentage error and the single worst hour. The bar chart breaks error down by delivery day, so you can see which days were hard to forecast. The histogram shows whether the forecast tends to run high or low. A positive bias here is flagged as overforecasting, not hidden.

### 2:35–2:55 — Methodology

**Screen:** `Methodology`.

**Do:** Scroll the "On this page" list, then stop on "Limitations".

> The Methodology page documents every choice: the data sources, the resolution mismatch between hourly forecasts and half-hourly actuals, how the cut-off works, the formulas, and the limitations. All of it is written down so the numbers can be checked or challenged.

### 2:55–3:05 — Close

**Screen:** Back to Overview.

> To be clear about scope: there are no price or procurement models here, values are megawatts exactly as Elexon supplies them, and nothing is estimated or filled in. It is a read-only analytics tool, live on Vercel and Render.

## Feature map — which feature is on which page

| Page (URL) | Feature | Where exactly |
|---|---|---|
| All pages | API status pill | Top bar, right side; click the refresh icon |
| All pages | Navigation | Left sidebar on desktop, bottom bar on mobile |
| All pages | Fixture-mode warning banner | Appears only when `DATA_MODE=fixture` |
| `/overview` | 4 KPI cards | Main grid under the header |
| `/overview` | Coverage definition note | Footnote under the coverage card |
| `/overview` | Decision-context audit panel | Right/below KPIs: rule, first/last cut-off, publication range, lead time, resolution |
| `/overview` | Data source & freshness | Panel with Live/Synthetic dot, source name, fetch time, records inspected, cache TTL, dependency health |
| All analysis pages | Analysis window filter | Delivery from / to, cut-off mode (Daily D-1 or Fixed), cut-off time, `Load January 2026`, `Apply`, `Reset` |
| `/explorer` | Forecast vs outturn chart | Top panel, yellow hourly forecast vs grey 30-minute outturn |
| `/explorer` | Summary strip | Coverage, valid pairs, missing forecast, missing outturn, distinct publications |
| `/explorer` | Interval table | Below the chart, 50 rows per page with pagination |
| `/explorer` | Status filters | Above the table: All intervals, No forecast, missing outturn, missing both |
| `/explorer` | Row details | `Details` button on each row — publication, cut-off, lead time, previous eligible publication, error fields |
| `/explorer` | CSV export | Download icon above the table; exports the currently filtered rows |
| `/accuracy` | Metric cards | MAE, RMSE, MBE (with Overforecast badge), MAPE, Largest absolute miss |
| `/accuracy` | Daily error chart | "Mean absolute error by delivery day" |
| `/accuracy` | Error distribution | "Signed forecast error" histogram |
| `/accuracy` | Daily table | Bottom table, per-day metrics |
| `/accuracy` | Low-coverage warning | Yellow notice when coverage is below the threshold |
| `/methodology` | Scope in/out | First section, two-column list |
| `/methodology` | Sources & resolution | Dataset cards for FUELHH and WINDFOR |
| `/methodology` | Decision cut-off and selection rules | Middle sections |
| `/methodology` | Metrics formulas | Each metric defined with formula and interpretation |
| `/methodology` | Data quality and limitations | Lower sections; read the limitations on camera |
| `/methodology` | Reproducibility | Final section |
| API (`/docs`) | Swagger UI and all endpoints | https://wind-forecast-e9oq.onrender.com/docs |
| API (`/api/health`) | Health, mode, dependency and cache status | https://wind-forecast-e9oq.onrender.com/api/health |

## Things not to claim on camera

- Do not say the tool predicts prices, demand, or savings.
- Do not say half-hourly forecasts exist; only outturn is half-hourly.
- Do not present fixture data as Elexon data.
- Do not promise instant loading; the free Render instance sleeps and may take 30–60 seconds on the first request.
