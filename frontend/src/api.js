// Single place that talks to the backend. Point BASE at the stdlib mock server
// (python scripts/mock_server.py) OR the FastAPI backend — same routes, same shapes.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
async function post(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export const api = {
  health: () => get("/health"),
  graph: () => get("/graph"),
  timeline: () => get("/timeline"),
  benchmark: () => get("/benchmark"),
  compare: (q) => get(`/recall/compare?query=${encodeURIComponent(q)}`),
  recall: (query, mode) => post("/recall", { query, mode }),
  hunch: (text, session_id) => post("/hunch", { text, session_id }),
  resolve: (session_ids) => post("/resolve", { session_ids }),
  expunge: (dataset) => post("/expunge", { dataset }),
};
