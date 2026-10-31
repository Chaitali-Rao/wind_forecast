import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { dayTime, gwh, longDate, mw, pct, timeOf } from "../format.js";
import Stat from "./Stat.jsx";
import useAsync from "./useAsync.js";

function ChartTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const hasBand = Number.isFinite(p.low) && Number.isFinite(p.high);
  return (
    <div className="tip">
      <strong>{timeOf(p.t)}</strong>
      <div className="row"><i className="dot f" /> Forecast <b>{mw(p.forecast)} MW</b></div>
      <div className="row"><i className="dot r" /> Likely range <b>{hasBand ? `${mw(p.low)}–${mw(p.high)} MW` : "unavailable"}</b></div>
      <div className="row"><i className="dot a" /> Actual <b>{p.actual == null ? "not yet known" : `${mw(p.actual)} MW`}</b></div>
      <div className="muted">Forecast made {dayTime(p.published)}</div>
    </div>
  );
}

export default function DecisionView({ day, cutoff }) {
  const { data, error, loading } = useAsync(() => api.forecast(day, cutoff), [day, cutoff]);

  if (error) return <div className="notice error" role="alert">{error}</div>;
  if (!data) return <div className="notice">Loading forecast…</div>;

  const s = data.summary;
  const chart = data.series.map((r) => ({
    ...r,
    band: Number.isFinite(r.low) && Number.isFinite(r.high) ? r.high - r.low : null,
  }));
  const ticks = chart.filter((_, i) => i % 6 === 0).map((r) => r.t);
  const dm = s.day_metrics;
  const sameVintage = s.vintages_used === 1;

  return (
    <div className={loading ? "dim" : ""}>
      <section className="lead">
        <h2>Plan for {longDate(data.date)}</h2>
        <p>
          At your {cutoff} decision time, the latest forecast on hand was published{" "}
          <b>{dayTime(s.latest_publish)}</b>
          {!sameVintage && <> (the half-hours of the day draw on {s.vintages_used} different publications, oldest {dayTime(s.earliest_publish)})</>}.
          It expects <b>{gwh(s.forecast_mwh)} GWh</b> of wind over the day.
          {s.band.available ? <> The historical error-based range is between <b>{gwh(s.forecast_mwh_low)}</b> and <b>{gwh(s.forecast_mwh_high)} GWh</b>.</> : <> An uncertainty range is not shown because there is not enough prior-day history within the evaluation window.</>}
          Use this forecast alongside demand and other generation forecasts to estimate the residual procurement requirement.
        </p>
      </section>

      <section className="stats">
        <Stat label="Expected wind energy" value={gwh(s.forecast_mwh)} unit="GWh" note={`Average ${mw(s.forecast_mean_mw)} MW`} />
        <Stat label="Historical error range" value={s.band.available ? `${gwh(s.forecast_mwh_low)}–${gwh(s.forecast_mwh_high)}` : "Unavailable"} unit={s.band.available ? "GWh" : ""}
          note={s.band.basis} />
        <Stat label="Outcome" value={s.actual_mwh == null ? "Not yet known" : gwh(s.actual_mwh)} unit={s.actual_mwh == null ? "" : "GWh"}
          note={s.actual_mwh == null ? "Delivery day has not completed" : `Forecast was ${s.forecast_mwh >= s.actual_mwh ? "above" : "below"} by ${gwh(Math.abs(s.forecast_mwh - s.actual_mwh))} GWh`} />
        <Stat label="Typical miss that day" value={dm.n ? mw(dm.mae) : "–"} unit={dm.n ? "MW" : ""}
          note={dm.n ? `${pct(dm.nmae_pct)} of average output` : "Needs actuals"} />
      </section>

      <section className="chart-block" aria-label="Forecast versus actual wind generation">
        <h3>Wind generation by half-hour</h3>
        <div className="chart">
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="t" ticks={ticks} tickFormatter={timeOf} stroke="var(--muted)" tickLine={false} />
              <YAxis tickFormatter={(v) => (v / 1000).toFixed(0)} stroke="var(--muted)" tickLine={false} axisLine={false}
                label={{ value: "GW", position: "insideTopLeft", offset: 0, fill: "var(--muted)", dy: -8 }} />
              <Tooltip content={<ChartTip />} />
              <Legend verticalAlign="top" align="right" iconType="plainline" />
              <Area dataKey="low" stackId="b" stroke="none" fill="transparent" legendType="none" isAnimationActive={false} />
              <Area dataKey="band" stackId="b" name="Likely range" stroke="none" fill="var(--band)" isAnimationActive={false} />
              <Line dataKey="forecast" name="Forecast at decision time" stroke="var(--forecast)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
              <Line dataKey="actual" name="Actual" stroke="var(--ink)" strokeWidth={2} strokeDasharray="5 3" dot={false} connectNulls={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p className="muted small">
          {s.band.available
            ? "The shaded range adjusts the decision-time forecast using the 10th and 90th percentiles of signed errors from prior delivery days whose actuals would have been known by the decision cutoff. This is a historical empirical range, not a guaranteed prediction interval."
            : "No shaded range is shown because at least 48 prior half-hourly errors, from delivery days before the day-ahead decision date, are required. Future actuals are never used to fill this gap."}
        </p>
      </section>
    </div>
  );
}
