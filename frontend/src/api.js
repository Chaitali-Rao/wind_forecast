// VITE_API_URL is empty in Docker/dev (same-origin /api) and set to the backend URL on Vercel.
const BASE = import.meta.env.VITE_API_URL || "";

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  forecast: (date, cutoff) => get("/api/forecast", { date, cutoff }),
  metrics: (start, end, cutoff) => get("/api/metrics", { start, end, cutoff }),
  horizon: () => get("/api/horizon"),
};
