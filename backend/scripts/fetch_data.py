"""Download real Elexon data for January 2026 and cache it in backend/data/.

Run once from the backend/ folder:   python -m scripts.fetch_data
Commit the generated JSON files so the deployed app does not depend on Elexon being reachable.
"""
from datetime import date

from app import config
from app.elexon import fetch_actuals, fetch_forecasts
from app.store import save_real

if __name__ == "__main__":
    print("Fetching FUELHH (actual wind) ...")
    actuals = fetch_actuals(date.fromisoformat(config.DELIVERY_START), date.fromisoformat(config.DELIVERY_END))
    print(f"  {len(actuals)} rows")
    if not actuals.empty:
        print(f"  actual coverage: {actuals['start_time'].min()} .. {actuals['start_time'].max()}")
    print("Fetching WINDFOR (forecasts) ...")
    forecasts = fetch_forecasts(date.fromisoformat(config.PUBLISH_FETCH_FROM), date.fromisoformat(config.PUBLISH_FETCH_TO))
    print(f"  {len(forecasts)} rows")
    if not forecasts.empty:
        print(f"  forecast targets: {forecasts['start_time'].min()} .. {forecasts['start_time'].max()}")
        print(f"  publication times: {forecasts['publish_time'].min()} .. {forecasts['publish_time'].max()}")
    assert len(actuals) and len(forecasts), "No data returned - check the API docs / parameters in app/elexon.py"
    actual_days = actuals['start_time'].dt.tz_convert(config.MARKET_TZ).dt.date.nunique()
    forecast_days = forecasts['start_time'].dt.tz_convert(config.MARKET_TZ).dt.date.nunique()
    print(f"  covered delivery days: actuals={actual_days}/31, forecast targets={forecast_days}/31")
    if actual_days < 28 or forecast_days < 28:
        raise RuntimeError("Data coverage is unexpectedly low; do not use this cache for submission. Inspect API filters and returned records.")
    save_real(actuals, forecasts)
    print(f"Saved to {config.DATA_DIR}")
