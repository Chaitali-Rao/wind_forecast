import { useEffect, useState } from "react";
import { api } from "./api.js";
import DecisionView from "./components/DecisionView.jsx";
import AccuracyView from "./components/AccuracyView.jsx";

const DEFAULT_DAY = "2026-01-15";

export default function App() {
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("decision");
  const [day, setDay] = useState(DEFAULT_DAY);
  const [cutoff, setCutoff] = useState("09:00");

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); setCutoff(m.default_cutoff); }).catch((e) => setError(e.message));
  }, []);

  const shift = (n) => {
    const d = new Date(`${day}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + n);
    const next = d.toISOString().slice(0, 10);
    if (meta && next >= meta.delivery_start && next <= meta.delivery_end) setDay(next);
  };

  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>Wind forecast monitor</h1>
          <p className="sub">GB day-ahead buying desk · national wind generation</p>
        </div>
        {meta?.data_source === "sample" && (
          <span className="badge warn" title="Real Elexon data has not been loaded. Run the fetch script (see README).">
            Demo data – not real Elexon values
          </span>
        )}
        {meta?.data_source === "elexon" && <span className="badge ok">Elexon data · FUELHH + WINDFOR</span>}
      </header>

      {error && (
        <div className="notice error" role="alert">
          Can't reach the API ({error}). Check that the backend is running and, on Vercel, that VITE_API_URL is set.
        </div>
      )}

      <section className="controls" aria-label="Decision settings">
        <div className="field">
          <label htmlFor="day">Delivery day</label>
          <div className="daypick">
            <button onClick={() => shift(-1)} aria-label="Previous day">‹</button>
            <input id="day" type="date" value={day} min={meta?.delivery_start} max={meta?.delivery_end}
              onChange={(e) => e.target.value && setDay(e.target.value)} />
            <button onClick={() => shift(1)} aria-label="Next day">›</button>
          </div>
        </div>
        <div className="field">
          <label htmlFor="cutoff">Decision time, day before (UK)</label>
          <input id="cutoff" type="time" value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
        </div>
        <nav className="tabs" role="tablist">
          <button role="tab" aria-selected={tab === "decision"} onClick={() => setTab("decision")}>Decision view</button>
          <button role="tab" aria-selected={tab === "accuracy"} onClick={() => setTab("accuracy")}>Forecast accuracy</button>
        </nav>
      </section>

      <main>
        {tab === "decision" ? <DecisionView day={day} cutoff={cutoff} /> : <AccuracyView cutoff={cutoff} meta={meta} />}
      </main>

      <footer>
        Wind actuals: Elexon FUELHH. Forecasts: Elexon WINDFOR. Times shown in UK local time. Error = forecast − actual.
      </footer>
    </div>
  );
}
