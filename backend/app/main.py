from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import analysis, config, store

app = FastAPI(title="Wind Forecast Monitor API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_decision_cache: dict[str, pd.DataFrame] = {}


def _cutoff(value: str) -> str:
    if not CUTOFF_RE.match(value):
        raise HTTPException(400, "cutoff must be HH:MM (24h, UK local time)")
    return value


def _date(value: str) -> date:
    try:
        d = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, f"invalid date '{value}', expected YYYY-MM-DD")
    if not (date.fromisoformat(config.DELIVERY_START) <= d <= date.fromisoformat(config.DELIVERY_END)):
        raise HTTPException(400, f"delivery date must be within {config.DELIVERY_START}..{config.DELIVERY_END}")
    return d


def _decision_frame(cutoff: str) -> pd.DataFrame:
    """Latest-forecast-at-cutoff joined with actuals (cached per cutoff)."""
    if cutoff not in _decision_cache:
        data = store.get()
        latest = analysis.latest_forecast_at_cutoff(data.forecasts, cutoff)
        _decision_cache[cutoff] = analysis.join_actuals(latest, data.actuals)
    return _decision_cache[cutoff]


def _iso(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    data = store.get()
    return {
        "data_source": data.source,
        "fetched_at": data.fetched_at,
        "delivery_start": config.DELIVERY_START,
        "delivery_end": config.DELIVERY_END,
        "default_cutoff": config.DEFAULT_CUTOFF,
        "timezone": config.MARKET_TZ,
        "forecast_rows": int(len(data.forecasts)),
        "actual_rows": int(len(data.actuals)),
    }


@app.get("/api/forecast")
def forecast(date_: str = Query(..., alias="date"), cutoff: str = config.DEFAULT_CUTOFF):
    """What the buyer sees on D-1 at `cutoff` for delivery day `date`."""
    day, cutoff = _date(date_), _cutoff(cutoff)
    frame = _decision_frame(cutoff)
    rows, band = analysis.day_view(frame, day)
    if rows.empty:
        raise HTTPException(404, "no forecast available for that day and cutoff")

    series = [
        {
            "t": _iso(r.start_time),
            "forecast": analysis._f(r.forecast),
            "actual": analysis._f(r.actual),
            "low": analysis._f(r.low),
            "high": analysis._f(r.high),
            "published": _iso(r.publish_time),
        }
        for r in rows.itertuples()
    ]
    complete = rows["actual"].notna().all()
    summary = {
        "cutoff_utc": _iso(analysis.cutoff_utc(day, cutoff)),
        "vintages_used": int(rows["publish_time"].nunique()),
        "latest_publish": _iso(rows["publish_time"].max()),
        "earliest_publish": _iso(rows["publish_time"].min()),
        "forecast_mean_mw": analysis._f(rows["forecast"].mean()),
        "forecast_mwh": analysis._f(rows["forecast"].sum() * 0.5),  # MW x 0.5h
        "forecast_mwh_low": analysis._f(rows["low"].sum() * 0.5) if band["available"] else None,
        "forecast_mwh_high": analysis._f(rows["high"].sum() * 0.5) if band["available"] else None,
        "actual_mwh": analysis._f(rows["actual"].sum() * 0.5) if complete else None,
        "day_metrics": analysis.metrics(rows),
        "band": band,
        "periods": int(len(rows)),
    }
    return {"date": day.isoformat(), "cutoff": cutoff, "series": series, "summary": summary}


@app.get("/api/metrics")
def get_metrics(start: str = config.DELIVERY_START, end: str = config.DELIVERY_END, cutoff: str = config.DEFAULT_CUTOFF):
    """Forecast accuracy for decisions made at `cutoff`, over delivery days start..end."""
    s, e, cutoff = _date(start), _date(end), _cutoff(cutoff)
    if s > e:
        raise HTTPException(400, "start must be <= end")
    frame = analysis.add_delivery_date(_decision_frame(cutoff))
    frame = frame[(frame["delivery_date"] >= s) & (frame["delivery_date"] <= e)]
    return {
        "start": s.isoformat(),
        "end": e.isoformat(),
        "cutoff": cutoff,
        "overall": analysis.metrics(frame),
        "by_hour": analysis.by_hour(frame),
        "daily": analysis.daily(frame),
    }


@app.get("/api/horizon")
def horizon(bucket_hours: int = Query(6, ge=1, le=24)):
    """Accuracy of all forecast vintages by lead time (how far ahead they were made)."""
    data = store.get()
    return {"bucket_hours": bucket_hours, "buckets": analysis.by_horizon(data.forecasts, data.actuals, bucket_hours)}
