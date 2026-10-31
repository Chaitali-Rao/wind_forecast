import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { mw, pct, shortDate } from "../format.js";
import Stat from "./Stat.jsx";
import useAsync from "./useAsync.js";

const axis = { stroke: "var(--muted)", tickLine: false };
const gw = (v) => (v / 1000).toFixed(1);

export default function AccuracyView({ cutoff, meta }) {
  const [range, setRange] = useState({ start: meta?.delivery_start || "2026-01-01", end: meta?.delivery_end || "2026-01-31" });
  const m = useAsync(() => api.metrics(range.start, range.end, cutoff), [range.start, range.end, cutoff]);
  const h = useAsync(() => api.horizon(), []);

  if (m.error) return <div className="notice error" role="alert">{m.error}</div>;
  if (!m.data) return <div className="notice">Loading accuracy…</div>;

  const o = m.data.overall;
  const dir = o.bias > 0 ? "higher" : "lower";
  const daily = m.data.daily.map((d) => ({ ...d, label: shortDate(d.date) }));
  const hours = m.data.by_hour.map((d) => ({ ...d, label: `${String(d.hour).padStart(2, "0")}:00` }));
  const horizon = (h.data?.buckets || []).map((b) => ({ ...b, label: `${b.from_h}–${b.to_h}h` }));

  return (
    <div className={m.loading ? "dim" : ""}>
      <section className="lead">
        <h2>How wrong is the forecast you buy on?</h2>
        <p>
          For decisions made at {cutoff} on the day before delivery, the forecast was off by <b>{mw(o.mae)} MW</b> on average
          ({pct(o.nmae_pct)} of average wind output). In 9 of 10 half-hours the miss was under <b>{mw(o.p90_abs)} MW</b>.
          Forecasts ran on average <b>{mw(Math.abs(o.bias))} MW {dir}</b> than what was generated.
        </p>
        <div className="range">
          <label>From <input type="date" value={range.start} min={meta?.delivery_start} max={range.end}
            onChange={(e) => e.target.value && setRange({ ...range, start: e.target.value })} /></label>
          <label>To <input type="date" value={range.end} min={range.start} max={meta?.delivery_end}
            onChange={(e) => e.target.value && setRange({ ...range, end: e.target.value })} /></label>
          <span className="muted small">{o.n.toLocaleString("en-GB")} half-hours compared</span>
        </div>
      </section>

      <section className="stats five">
        <Stat label="Mean absolute error" value={mw(o.mae)} unit="MW" note="Average size of the miss" />
        <Stat label="Root mean square error" value={mw(o.rmse)} unit="MW" note="Penalises big misses more" />
        <Stat label="Bias" value={`${o.bias > 0 ? "+" : "−"}${mw(Math.abs(o.bias))}`} unit="MW" note="Forecast − actual, averaged" />
        <Stat label="90th percentile miss" value={mw(o.p90_abs)} unit="MW" note="Size of a bad half-hour" />
        <Stat label="Worst miss" value={mw(o.max_abs)} unit="MW" note="Single largest error" />
      </section>

      <section className="grid2">
        <div className="chart-block">
          <h3>Average miss by delivery day</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={daily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="label" interval={Math.ceil(daily.length / 10) - 1} {...axis} />
              <YAxis tickFormatter={gw} {...axis} axisLine={false} label={{ value: "GW", position: "insideTopLeft", fill: "var(--muted)", dy: -8 }} />
              <Tooltip formatter={(v) => `${mw(v)} MW`} labelFormatter={(l) => l} />
              <Bar dataKey="mae" name="Mean absolute error" fill="var(--forecast)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-block">
          <h3>Bias by hour of day</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={hours} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="label" interval={2} {...axis} />
              <YAxis tickFormatter={gw} {...axis} axisLine={false} label={{ value: "GW", position: "insideTopLeft", fill: "var(--muted)", dy: -8 }} />
              <ReferenceLine y={0} stroke="var(--ink)" />
              <Tooltip formatter={(v) => `${mw(v)} MW`} />
              <Bar dataKey="bias" name="Bias (forecast − actual)" isAnimationActive={false}>
                {hours.map((d) => <Cell key={d.hour} fill={d.bias > 0 ? "var(--warn)" : "var(--forecast)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="muted small"><i className="dot w" /> above zero = forecast too high · <i className="dot f" /> below zero = forecast too low</p>
        </div>
      </section>

      <section className="chart-block">
        <h3>Does waiting help? Error by how far ahead the forecast was made</h3>
        {h.loading && !h.data ? <p className="muted">Loading…</p> : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={horizon} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="label" {...axis} />
              <YAxis tickFormatter={gw} {...axis} axisLine={false} label={{ value: "GW", position: "insideTopLeft", fill: "var(--muted)", dy: -8 }} />
              <Tooltip formatter={(v) => `${mw(v)} MW`} />
              <Legend verticalAlign="top" align="right" />
              <Line dataKey="mae" name="Mean absolute error" stroke="var(--forecast)" strokeWidth={2.5} dot isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
        <p className="muted small">
          Uses every published forecast, not only the one available at your cutoff. Forecasts made closer to the delivery
          time are generally more accurate, which shows what an earlier decision costs you.
        </p>
      </section>
    </div>
  );
}
