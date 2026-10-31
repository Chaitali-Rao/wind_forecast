"""Synthetic demo data, used ONLY when real Elexon data is not available.

It mimics the shape of the real datasets (30-min targets, forecasts published
every 3h with error that grows with horizon) so the app can be developed and
demoed offline. The UI shows a clear "demo data" badge whenever this is used.
"""
import numpy as np
import pandas as pd

CAPACITY_MW = 20000.0


def make_sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    idx = pd.date_range("2025-12-25", "2026-02-01", freq="30min", tz="UTC", inclusive="left")
    n = len(idx)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.995 * x[i - 1] + rng.normal(0, 0.08)
    actual = CAPACITY_MW / (1 + np.exp(-(2.2 * x - 0.4)))
    actual = np.clip(actual + rng.normal(0, 80, n), 200, CAPACITY_MW)
    actuals = pd.DataFrame({"start_time": idx, "actual": actual.round(0)})
    lookup = actuals.set_index("start_time")["actual"]

    rows = []
    pubs = pd.date_range("2025-12-28", "2026-01-31 21:00", freq="3h", tz="UTC")
    for p in pubs:
        offset = rng.normal(0, 150)  # vintage-wide error
        steps = np.arange(1, 97)  # 0.5h .. 48h ahead
        targets = p + pd.to_timedelta(steps * 30, unit="m")
        targets = targets[targets.isin(lookup.index)]
        h = ((targets - p).total_seconds() / 3600).to_numpy()
        sd = 150 + 30 * h
        fc = lookup.loc[targets].to_numpy() * 0.98 + offset + rng.normal(0, sd)
        fc = np.clip(fc, 0, CAPACITY_MW)
        rows.append(pd.DataFrame({"start_time": targets, "publish_time": p, "forecast": fc.round(0)}))
    forecasts = pd.concat(rows, ignore_index=True)
    forecasts = forecasts.sort_values(["start_time", "publish_time"]).reset_index(drop=True)
    return actuals, forecasts
