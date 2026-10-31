# Wind Forecast Monitor

A web app for a GB energy utility's day-ahead buying desk. It answers two questions about **national wind generation**:

1. **What is the latest wind forecast available when I have to buy for tomorrow?**
2. **How wrong are those forecasts, in numbers I can plan around?**

Data: Elexon Insights API only – `FUELHH` (actuals, `fuelType = WIND`) and `WINDFOR` (forecasts). Scope: delivery days **1–31 January 2026**.

**Live app:** Add the verified public Vercel URL here after deployment. Do not submit while this placeholder remains.

> **AI disclosure:** AI tools (Anthropic Claude and OpenAI ChatGPT) were used to assist with code review, selected code changes, design/documentation suggestions, and test development. The author is responsible for reviewing, testing, and validating the submitted implementation.

---

## The key idea

Forecasts are re-issued many times. For a half-hour on day **D**, the buyer decides on day **D-1** at a fixed time (the *cutoff*, default **09:00 UK time**, configurable in the UI). So for each half-hour we use the **most recent forecast with `publishTime ≤ cutoff`**, and ignore anything published later – the buyer could not have seen it. That "decision-time forecast" is then compared to the actual (`FUELHH`) to produce the accuracy numbers.

Assumptions (also stated in the UI/video):
- Cutoff defaults to 09:00 UK time on D-1 (day-ahead auctions close shortly after). Change it in the UI or `DEFAULT_CUTOFF`.
- Only the first 48 h of lead time are kept (`MAX_HORIZON_HOURS`) – enough for any D-1 decision.
- Error = forecast − actual. Positive means the forecast was too high.
- The historical error range uses the 10th/90th percentile of signed errors from delivery days strictly before D-1. It never uses future actuals. Since the evaluation window starts on 1 January, the range is intentionally unavailable for early delivery dates until at least 48 eligible prior half-hourly errors exist. This avoids look-ahead leakage.

## Repository layout

```
backend/
  app/
    config.py      settings (cutoff, dates, timezone, Elexon URL)
    elexon.py      Elexon API client (FUELHH + WINDFOR) - parameter names live here
    store.py       loads data once: cached real files -> optional live fetch -> demo data
    sample.py      synthetic demo data (only used if real data is missing)
    analysis.py    pure functions: latest-forecast-at-cutoff, metrics, by-hour, by-horizon
    main.py        FastAPI routes under /api
  api/index.py     Vercel serverless entrypoint
  scripts/fetch_data.py   download real January 2026 data into backend/data/
  tests/test_analysis.py  unit tests for the core logic
  data/            cached real data (commit it after fetching)
frontend/          React (Vite) + Recharts
  src/App.jsx, api.js, format.js, styles.css
  src/components/  DecisionView, AccuracyView, Stat, useAsync
docker-compose.yml  backend (port 8000) + frontend via nginx (port 3000)
docs/              ARCHITECTURE.md, VIDEO_SCRIPT.md, SUBMISSION_CHECKLIST.md
```

## Run it

### With Docker (recommended)
```bash
docker compose up --build
# open http://localhost:3000
```
On first start Docker tries to download real data from Elexon into `backend/data/`. If the API is unreachable, the local app can run with synthetic sample data and shows an orange **"Demo data"** badge. Do not use sample data for the submitted demo. Verify `/api/meta` reports `data_source: "elexon"` before recording.

### Without Docker
```bash
# backend
cd backend
pip install -r requirements.txt
python -m scripts.fetch_data          # downloads real data (needs internet)
uvicorn app.main:app --reload         # http://localhost:8000/docs

# frontend (new terminal)
cd frontend
npm install
npm run dev                           # http://localhost:5173 (proxies /api to :8000)
```

### Tests
```bash
cd backend && python -m pytest -q
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/meta` | data source, date range, default cutoff |
| `GET /api/forecast?date=2026-01-15&cutoff=09:00` | decision-time forecast, actuals, likely range, summary for one delivery day |
| `GET /api/metrics?start=&end=&cutoff=` | MAE, RMSE, bias, P90, by-hour and daily breakdowns |
| `GET /api/horizon` | error by lead time across all forecast vintages |

## Deploy on Vercel (two projects from one repo)

1. **Backend:** import the repo, set *Root Directory* = `backend`. Make sure `backend/data/*.json` is committed (run `fetch_data` first). Note the URL.
2. **Frontend:** import the repo again, *Root Directory* = `frontend`, add env var `VITE_API_URL` = the backend URL (no trailing slash).
3. Set `REQUIRE_REAL_DATA=true` in the backend deployment environment. This makes the backend fail loudly if the real cache is missing instead of serving synthetic values.
4. Make sure `backend/data/fuelhh_wind.json`, `backend/data/windfor.json`, and `backend/data/meta.json` are committed to the public repo after a successful fetch.
5. Put the verified frontend URL at the top of this README and test the app/API in an incognito window.

## Key development practices
- Analysis logic is pure functions, separated from I/O and HTTP, and unit-tested (cutoff, BST, "latest before cutoff", metrics, horizon buckets).
- Input validation on all endpoints (date range, `HH:MM` cutoff).
- Real data is cached to disk so the deployed app does not depend on Elexon being reachable.
- Honest data labelling: the UI never silently shows demo data as real.
- Production guard: set `REQUIRE_REAL_DATA=true` so a deployment without cached Elexon data fails rather than silently serving synthetic data.
- No-look-ahead validation: uncertainty-band history excludes delivery dates on or after D-1; tests cover the insufficient-history path.
