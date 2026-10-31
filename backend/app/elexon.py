"""Thin client for the two Elexon Insights datasets we use.

Parameter names are defined in ONE place (below) so that if the API docs differ
from what is written here, there is exactly one spot to fix.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd

from .config import ELEXON_BASE_URL, MAX_HORIZON_HOURS


def _get(client: httpx.Client, path: str, params: dict[str, Any]) -> list[dict]:
    resp = client.get(
        f"{ELEXON_BASE_URL}{path}",
        params=params,
        headers={"Accept": "application/json"},
        timeout=90,
    )
    resp.raise_for_status()
    payload = resp.json()
    # Stream endpoints return a bare JSON array; other endpoints wrap in {"data": [...]}.
    return payload["data"] if isinstance(payload, dict) else payload


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    """Actual wind generation (FUELHH, fuelType == WIND), 30-minute resolution."""
    rows: list[dict] = []
    with httpx.Client() as client:
        cur = start
        while cur <= end:
            chunk_end = min(cur + timedelta(days=6), end)
            rows += _get(
                client,
                "/datasets/FUELHH/stream",
                {
                    "settlementDateFrom": cur.isoformat(),
                    "settlementDateTo": chunk_end.isoformat(),
                    "fuelType": "WIND",
                },
            )
            cur = chunk_end + timedelta(days=1)
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["start_time", "actual"])
    df = df[df["fuelType"] == "WIND"]
    out = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "actual": pd.to_numeric(df["generation"]),
        }
    )
    return out.drop_duplicates("start_time").sort_values("start_time").reset_index(drop=True)


def fetch_forecasts(publish_from: date, publish_to: date) -> pd.DataFrame:
    """All WINDFOR forecasts published in [publish_from, publish_to]."""
    rows: list[dict] = []
    with httpx.Client() as client:
        cur = publish_from
        while cur <= publish_to:
            chunk_end = min(cur + timedelta(days=1), publish_to)
            frm = datetime(cur.year, cur.month, cur.day, tzinfo=timezone.utc)
            to = datetime(chunk_end.year, chunk_end.month, chunk_end.day, 23, 59, 59, tzinfo=timezone.utc)
            rows += _get(
                client,
                "/datasets/WINDFOR/stream",
                {
                    "publishDateTimeFrom": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            cur = chunk_end + timedelta(days=1)
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["start_time", "publish_time", "forecast"])
    out = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "forecast": pd.to_numeric(df["generation"]),
        }
    )
    horizon_h = (out["start_time"] - out["publish_time"]).dt.total_seconds() / 3600
    out = out[(horizon_h >= 0) & (horizon_h <= MAX_HORIZON_HOURS)]
    return (
        out.drop_duplicates(["start_time", "publish_time"])
        .sort_values(["start_time", "publish_time"])
        .reset_index(drop=True)
    )
