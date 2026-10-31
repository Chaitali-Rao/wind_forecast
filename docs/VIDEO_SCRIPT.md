# Video script (max 10 minutes, unlisted YouTube)

Tip: rehearse once, then record the screen with your voice. Keep each part to ~4:30 so you stay under 10:00.

## Part 1 – Client pitch (target 4:30)

**0:00 – The problem (30s)**
"Every morning you buy tomorrow's power. Wind is free but uncertain, so the real question is: how much do I still need to buy from thermal plants – and how much can I trust the wind forecast?"

**0:30 – Decision view (90s)** *(open the app, pick a day, e.g. 15 Jan)*
- "Pick the delivery day and your decision time. The app shows the latest forecast you would actually have had – nothing published after your cutoff."
- Point at the headline sentence: expected GWh and the historical error-based range, if enough prior history exists. For early January dates, explain that the app intentionally withholds the range rather than using future actuals.
- Point at the chart: teal = forecast at decision time, dashed = what really happened, shaded = likely range.

**2:00 – Accuracy (90s)** *(switch tab)*
- "Over January, the forecast missed by X MW on average, Y% of output. On a bad half-hour, by Z MW."
- Bias: "Forecasts ran high/low by N MW – you can correct for that."
- By hour: "Errors are larger at these hours."

**3:30 – Does waiting help? (45s)**
- "Forecasts made closer to delivery are more accurate – here is exactly how much."

**4:15 – Close (15s)**
"With this you buy with a number on the risk, not just a forecast. Happy to extend it to your own cutoff time and more data."

## Part 2 – Tech lead review (target 4:30)

**5:00 – Architecture (60s)** – show docs/ARCHITECTURE.md diagram. Elexon → cached JSON → pandas analysis → FastAPI → React.

**6:00 – The core logic (90s)** – open `backend/app/analysis.py`, `latest_forecast_at_cutoff`:
filter `publish_time <= cutoff`, sort, keep last per target. Explain cutoff = D-1 09:00 London time, BST-safe.

**7:30 – Metrics & band (60s)** – `metrics`, `day_view` (strict no-look-ahead; range omitted when history is insufficient), `by_horizon`.

**8:30 – Code layout & practices (45s)** – config / elexon / store / analysis / main; tests (`pytest`), validation, Docker, Vercel setup.

**9:15 – Trade-offs & next steps (30s)** – cached data vs live; assumptions; what you would do with more time. Mention AI tools were used.

**9:45 – End.**
