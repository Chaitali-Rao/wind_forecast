const TZ = "Europe/London";

export const mw = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-GB"));
export const gwh = (mwh) => (mwh == null ? "–" : (mwh / 1000).toLocaleString("en-GB", { maximumFractionDigits: 1 }));
export const pct = (v) => (v == null ? "–" : `${v.toFixed(1)}%`);

export const timeOf = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const dayTime = (iso) =>
  new Date(iso).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const longDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });

export const shortDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

export const prevDay = (isoDate) => {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
};
