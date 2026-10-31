"""Loads actuals + forecasts once and keeps them in memory.

Priority: cached real files in DATA_DIR  ->  (optional) live Elexon fetch  ->  synthetic sample.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import config
from .sample import make_sample

log = logging.getLogger("store")
ACTUALS_FILE = "fuelhh_wind.json"
FORECASTS_FILE = "windfor.json"
META_FILE = "meta.json"


@dataclass
class Data:
    actuals: pd.DataFrame
    forecasts: pd.DataFrame
    source: str  # "elexon" | "sample"
    fetched_at: str | None = None


def save_real(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    a = actuals.assign(start_time=actuals["start_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    f = forecasts.assign(
        start_time=forecasts["start_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        publish_time=forecasts["publish_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    (config.DATA_DIR / ACTUALS_FILE).write_text(json.dumps(a.values.tolist(), separators=(",", ":")))
    (config.DATA_DIR / FORECASTS_FILE).write_text(json.dumps(f.values.tolist(), separators=(",", ":")))
    (config.DATA_DIR / META_FILE).write_text(
        json.dumps({"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "source": "elexon"})
    )


def _load_real() -> Data | None:
    a_path, f_path = config.DATA_DIR / ACTUALS_FILE, config.DATA_DIR / FORECASTS_FILE
    if not (a_path.exists() and f_path.exists()):
        return None
    actuals = pd.DataFrame(json.loads(a_path.read_text()), columns=["start_time", "actual"])
    forecasts = pd.DataFrame(
        json.loads(f_path.read_text()), columns=["start_time", "publish_time", "forecast"]
    )
    if actuals.empty or forecasts.empty:
        log.warning("Cached Elexon files exist but one or both are empty; treating cache as unavailable")
        return None
    actuals["start_time"] = pd.to_datetime(actuals["start_time"], utc=True)
    for c in ("start_time", "publish_time"):
        forecasts[c] = pd.to_datetime(forecasts[c], utc=True)
    meta_path = config.DATA_DIR / META_FILE
    fetched = json.loads(meta_path.read_text()).get("fetched_at") if meta_path.exists() else None
    return Data(actuals, forecasts, "elexon", fetched)


def _restrict_to_january(df: pd.DataFrame) -> pd.DataFrame:
    lo = pd.Timestamp(config.DELIVERY_START, tz=config.MARKET_TZ).tz_convert("UTC")
    hi = (pd.Timestamp(config.DELIVERY_END, tz=config.MARKET_TZ) + pd.Timedelta(days=1)).tz_convert("UTC")
    return df[(df["start_time"] >= lo) & (df["start_time"] < hi)].reset_index(drop=True)


def load() -> Data:
    data = _load_real()
    if data is None and config.LIVE_FETCH_ON_START:
        try:
            from .elexon import fetch_actuals, fetch_forecasts

            log.info("Fetching live data from Elexon ...")
            a = fetch_actuals(date.fromisoformat(config.DELIVERY_START), date.fromisoformat(config.DELIVERY_END))
            f = fetch_forecasts(
                date.fromisoformat(config.PUBLISH_FETCH_FROM), date.fromisoformat(config.PUBLISH_FETCH_TO)
            )
            if len(a) and len(f):
                save_real(a, f)
                data = _load_real()
        except Exception as exc:  # network down, API change, ...
            log.warning("Live fetch failed (%s); falling back to sample data", exc)
    if data is None:
        if config.REQUIRE_REAL_DATA:
            raise RuntimeError(
                "Real Elexon cache is missing. Run `python -m scripts.fetch_data` "
                "and deploy backend/data/fuelhh_wind.json plus backend/data/windfor.json."
            )
        a, f = make_sample()
        data = Data(a, f, "sample")
    data.actuals = _restrict_to_january(data.actuals)
    data.forecasts = _restrict_to_january(data.forecasts)
    return data


_cache: Data | None = None


def get() -> Data:
    global _cache
    if _cache is None:
        _cache = load()
    return _cache
