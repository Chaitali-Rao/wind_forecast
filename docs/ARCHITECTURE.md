# Architecture notes (for the tech-lead review)

```
 Elexon Insights API
   FUELHH (actual)   WINDFOR (forecast)
          \               /
        scripts/fetch_data.py  ──►  backend/data/*.json   (cached, committed)
                                         │
                                   app/store.py  (loaded once into pandas)
                                         │
   app/analysis.py (pure functions) ◄────┘
        │  latest_forecast_at_cutoff → join_actuals → metrics / by_hour / by_horizon / day_view
        ▼
   app/main.py  FastAPI  /api/forecast /api/metrics /api/horizon /api/meta
        ▼
   React (Vite) + Recharts:  Decision view | Forecast accuracy
```

## Why these choices
- **Cache, don't call Elexon per request.** Faster, works on serverless, and survives API downtime. Volume is small (~1.5k actual rows, tens of thousands of forecast rows).
- **pandas for the join.** The core operation is "latest row per target where publish_time <= cutoff" – a sort + drop_duplicates, easy to read and verify.
- **Cutoff is a parameter, not a constant.** The buyer's real gate time is a business assumption; making it adjustable lets the client test sensitivity.
- **Time zones.** Data is UTC; the cutoff is defined in Europe/London (handles BST); delivery day is the UK-local date. January is GMT so the two coincide, but the code does not rely on that (see `test_cutoff_respects_bst`).
- **Uncertainty band without look-ahead.** Uses signed-error quantiles from days before D-1 only; omits the band if fewer than 48 eligible intervals exist instead of leaking future data.
- **Separate Vercel projects.** FastAPI as a serverless function (`backend/api/index.py`), React as a static build.

## Known limitations / next steps
- Elexon parameter names are in `app/elexon.py` only; verify against the live API docs when first fetching.
- Error band is national, empirical and ignores wind-level dependence (errors are larger when output is high).
- Only wind; no demand, solar, or price data (out of scope by design).
- Possible extensions: per-cutoff sensitivity chart, CSV export, scheduled data refresh.
