"""Pure functions (no I/O) so they are easy to unit-test.

Vocabulary
  target / start_time : the half-hour being forecast
  publish_time        : when a forecast was created
  delivery date       : UK-local calendar date of the target
  cutoff              : the moment on D-1 (UK local) when the buying decision is made
  vintage             : one forecast publication (all targets sharing a publish_time)
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from .config import MARKET_TZ


def parse_cutoff(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def cutoff_utc(delivery_date: date, hhmm: str) -> pd.Timestamp:
    """UTC instant of the decision cutoff for a delivery date (D-1 at hh:mm UK time)."""
    local = datetime.combine(delivery_date - timedelta(days=1), parse_cutoff(hhmm))
    return pd.Timestamp(local).tz_localize(MARKET_TZ).tz_convert("UTC")


def add_delivery_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["delivery_date"] = out["start_time"].dt.tz_convert(MARKET_TZ).dt.date
    return out


def latest_forecast_at_cutoff(forecasts: pd.DataFrame, hhmm: str) -> pd.DataFrame:
    """For every target half-hour, keep the most recent forecast published
    at or before the D-1 cutoff. Forecasts published later are ignored,
    because the buyer could not have seen them when deciding."""
    f = add_delivery_date(forecasts)
    cutoffs = {d: cutoff_utc(d, hhmm) for d in f["delivery_date"].unique()}
    f["cutoff"] = f["delivery_date"].map(cutoffs)
    f = f[f["publish_time"] <= f["cutoff"]]
    f = f.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    return f.reset_index(drop=True)


def join_actuals(forecast_df: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    df = forecast_df.merge(actuals, on="start_time", how="left")
    df["error"] = df["forecast"] - df["actual"]  # + = over-forecast (buyer under-buys thermal)
    df["abs_error"] = df["error"].abs()
    return df


def _f(x) -> float | None:
    return None if x is None or pd.isna(x) else float(round(x, 2))


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual"])
    n = len(d)
    if n == 0:
        return {"n": 0}
    e, ae = d["error"], d["abs_error"]
    mean_actual = d["actual"].mean()
    return {
        "n": int(n),
        "mae": _f(ae.mean()),
        "rmse": _f(np.sqrt((e**2).mean())),
        "bias": _f(e.mean()),
        "nmae_pct": _f(ae.mean() / mean_actual * 100) if mean_actual else None,
        "p50_abs": _f(ae.quantile(0.5)),
        "p90_abs": _f(ae.quantile(0.9)),
        "max_abs": _f(ae.max()),
        "err_p10": _f(e.quantile(0.1)),
        "err_p90": _f(e.quantile(0.9)),
        "mean_actual": _f(mean_actual),
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["actual"]).copy()
    d["hour"] = d["start_time"].dt.tz_convert(MARKET_TZ).dt.hour
    g = d.groupby("hour").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size"))
    return [{"hour": int(h), "mae": _f(r.mae), "bias": _f(r.bias), "n": int(r.n)} for h, r in g.iterrows()]


def daily(df: pd.DataFrame) -> list[dict]:
    d = add_delivery_date(df).dropna(subset=["actual"])
    out = []
    for day, g in d.groupby("delivery_date"):
        out.append(
            {
                "date": day.isoformat(),
                "mae": _f(g["abs_error"].mean()),
                "rmse": _f(np.sqrt((g["error"] ** 2).mean())),
                "bias": _f(g["error"].mean()),
                "mean_actual": _f(g["actual"].mean()),
                "n": int(len(g)),
            }
        )
    return out


def by_horizon(forecasts: pd.DataFrame, actuals: pd.DataFrame, bucket_h: int = 6) -> list[dict]:
    """Error of EVERY forecast vintage grouped by how far ahead it was made.
    Shows how much accuracy improves the later you decide."""
    d = forecasts.merge(actuals, on="start_time", how="inner")
    d["horizon_h"] = (d["start_time"] - d["publish_time"]).dt.total_seconds() / 3600
    d["error"] = d["forecast"] - d["actual"]
    d["abs_error"] = d["error"].abs()
    d["bucket"] = (d["horizon_h"] // bucket_h * bucket_h).astype(int)
    g = d.groupby("bucket").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size"))
    return [
        {"from_h": int(b), "to_h": int(b + bucket_h), "mae": _f(r.mae), "bias": _f(r.bias), "n": int(r.n)}
        for b, r in g.iterrows()
    ]


def day_view(df_all: pd.DataFrame, day: date) -> tuple[pd.DataFrame, dict]:
    """Rows for one delivery day and a leakage-safe empirical uncertainty band.

    The error distribution is built only from delivery dates strictly before D-1.
    At the decision cutoff on D-1, those are the only delivery-day actuals that
    could already have been observed. January is the requested evaluation window,
    so the first days may not have enough in-window history. In that case the band
    is deliberately unavailable rather than using future actuals or in-sample data.
    """
    d = add_delivery_date(df_all)
    history = d[(d["delivery_date"] < day - timedelta(days=1))].dropna(subset=["actual", "error"])
    today = d[d["delivery_date"] == day].copy()

    # Require at least one full day of half-hourly errors before estimating tails.
    if len(history) >= 48:
        q10 = history["error"].quantile(0.1)
        q90 = history["error"].quantile(0.9)
        basis = f"{history['delivery_date'].nunique()} prior day(s); no future data"
        today["low"] = (today["forecast"] - q90).clip(lower=0)
        today["high"] = (today["forecast"] - q10).clip(lower=0)
    else:
        q10 = q90 = np.nan
        basis = "Unavailable: insufficient prior-day history"
        today["low"] = np.nan
        today["high"] = np.nan

    info = {
        "available": bool(len(history) >= 48),
        "history_intervals": int(len(history)),
        "basis": basis,
        "err_p10": _f(q10),
        "err_p90": _f(q90),
    }
    return today.sort_values("start_time").reset_index(drop=True), info
