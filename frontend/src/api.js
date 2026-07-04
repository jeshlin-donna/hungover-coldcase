// Single place that talks to the backend.
// The backend auto-detects live vs degraded and serves mock-compatible data on port 8000.
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
  graphTemporal: (time) => get(`/graph/temporal${time ? `?time=${encodeURIComponent(time)}` : ""}`),
  timeline: () => get("/timeline"),
  contradictions: () => get("/contradictions"),
  benchmark: () => get("/benchmark"),
  compare: (query, dataset = "all") => get(`/recall/compare?query=${encodeURIComponent(query)}&dataset=${dataset}`),
  recall: (query, mode) => post("/recall", { query, mode }),
  hunch: (text, session_id) => post("/hunch", { text, session_id }),
  resolve: (session_ids) => post("/resolve", { session_ids }),
  expunge: (dataset) => post("/expunge", { dataset }),
  missingHours: () => get("/missing-hours"),
  nexus: (from_node, to_node) => post("/nexus", { from_node, to_node }),
  interrogation: (suspect_id, focus_case) => post("/interrogation", { suspect_id, focus_case }),
  whatif: (hypothesis, inject_edge) => post("/whatif", { hypothesis, inject_edge: inject_edge || {} }),
  ingestFile: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`${BASE}/ingest-file`, { method: "POST", body: fd }).then((r) => r.json());
  },
  transcribe: (blob, filename = "recording.webm") => {
    const fd = new FormData();
    fd.append("file", blob, filename);
    return fetch(`${BASE}/transcribe`, { method: "POST", body: fd }).then((r) => r.json());
  },
  chat: (message, history) => post("/chat", { message, history }),
  report: () => get("/report"),
  suspectTimeline: (suspect = "daniel-marsh") => get(`/suspect-timeline?suspect=${encodeURIComponent(suspect)}`),
};
