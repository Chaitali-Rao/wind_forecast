from datetime import date

import pandas as pd
import pytest

from app import analysis


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_cutoff_is_previous_day_local_time():
    # January = GMT, so local == UTC
    assert analysis.cutoff_utc(date(2026, 1, 15), "09:00") == ts("2026-01-14 09:00")


def test_cutoff_respects_bst():
    # July = BST (UTC+1): 09:00 local is 08:00 UTC
    assert analysis.cutoff_utc(date(2026, 7, 15), "09:00") == ts("2026-07-14 08:00")


def make_forecasts():
    target = ts("2026-01-15 12:00")
    return pd.DataFrame(
        {
            "start_time": [target] * 4,
            "publish_time": [ts("2026-01-13 20:00"), ts("2026-01-14 08:00"), ts("2026-01-14 09:00"), ts("2026-01-14 10:00")],
            "forecast": [1000.0, 2000.0, 3000.0, 4000.0],
        }
    )


def test_latest_forecast_ignores_forecasts_after_cutoff():
    out = analysis.latest_forecast_at_cutoff(make_forecasts(), "09:00")
    assert len(out) == 1
    assert out.loc[0, "forecast"] == 3000.0  # 09:00 is inclusive, 10:00 is not


def test_earlier_cutoff_picks_older_forecast():
    out = analysis.latest_forecast_at_cutoff(make_forecasts(), "08:30")
    assert out.loc[0, "forecast"] == 2000.0


def test_no_forecast_before_cutoff_drops_target():
    out = analysis.latest_forecast_at_cutoff(make_forecasts(), "07:00")
    assert out.loc[0, "forecast"] == 1000.0
    assert analysis.latest_forecast_at_cutoff(make_forecasts().iloc[1:], "07:00").empty


def test_metrics_known_values():
    df = pd.DataFrame(
        {
            "start_time": pd.date_range("2026-01-15", periods=4, freq="30min", tz="UTC"),
            "forecast": [110.0, 90.0, 130.0, 100.0],
            "actual": [100.0, 100.0, 100.0, 100.0],
        }
    )
    df["error"] = df["forecast"] - df["actual"]  # 10, -10, 30, 0
    df["abs_error"] = df["error"].abs()
    m = analysis.metrics(df)
    assert m["n"] == 4
    assert m["mae"] == 12.5
    assert m["bias"] == 7.5
    assert m["rmse"] == pytest.approx(((100 + 100 + 900 + 0) / 4) ** 0.5, abs=0.01)
    assert m["nmae_pct"] == 12.5


def test_metrics_ignores_missing_actuals():
    f = make_forecasts().iloc[:1]
    df = analysis.join_actuals(f, pd.DataFrame({"start_time": [], "actual": []}).astype({"start_time": "datetime64[ns, UTC]"}))
    assert analysis.metrics(df) == {"n": 0}


def test_by_horizon_buckets():
    f = pd.DataFrame(
        {"start_time": [ts("2026-01-15 12:00")] * 2, "publish_time": [ts("2026-01-15 10:00"), ts("2026-01-14 12:00")], "forecast": [110.0, 150.0]}
    )
    a = pd.DataFrame({"start_time": [ts("2026-01-15 12:00")], "actual": [100.0]})
    out = {b["from_h"]: b for b in analysis.by_horizon(f, a, 6)}
    assert out[0]["mae"] == 10.0 and out[24]["mae"] == 50.0


def test_day_view_never_uses_future_actuals_for_uncertainty_band():
    # The selected day and its future dates have actuals, but those must not be
    # used to create a band when there is insufficient prior history.
    rows = []
    for day in pd.date_range("2026-01-01", periods=4, freq="D"):
        for slot in range(48):
            start = day.tz_localize("UTC") + pd.Timedelta(minutes=30 * slot)
            rows.append({
                "start_time": start,
                "forecast": 1000.0,
                "publish_time": start - pd.Timedelta(hours=24),
                "actual": 900.0 if day.day == 3 else 1200.0,
                "error": 100.0 if day.day == 3 else -200.0,
                "abs_error": 100.0 if day.day == 3 else 200.0,
            })
    df = pd.DataFrame(rows)
    day_rows, band = analysis.day_view(df, date(2026, 1, 3))
    # For Jan 3, only delivery dates before Jan 2 are eligible; Jan 1 is eligible,
    # so this test has exactly 48 prior intervals and a band is available.
    assert band["available"] is True
    assert band["history_intervals"] == 48
    assert "no future data" in band["basis"]
    assert day_rows["low"].notna().all() and day_rows["high"].notna().all()


def test_day_view_does_not_fallback_to_future_data_when_history_is_short():
    rows = []
    for day in (1, 2, 3):
        for slot in range(48):
            start = pd.Timestamp(f"2026-01-{day:02d}", tz="UTC") + pd.Timedelta(minutes=30 * slot)
            rows.append({
                "start_time": start,
                "forecast": 1000.0,
                "publish_time": start - pd.Timedelta(hours=24),
                "actual": 900.0,
                "error": 100.0,
                "abs_error": 100.0,
            })
    df = pd.DataFrame(rows)
    # Jan 2 decision is made on Jan 1; Jan 1 delivery actuals are not available
    # before the Jan 1 decision cutoff in this simplified date-only eligibility rule.
    day_rows, band = analysis.day_view(df, date(2026, 1, 2))
    assert band["available"] is False
    assert band["history_intervals"] == 0
    assert day_rows["low"].isna().all() and day_rows["high"].isna().all()
