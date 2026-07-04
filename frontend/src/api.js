// Single place that talks to the backend.
// The backend auto-detects live vs degraded and serves mock-compatible data on port 8000.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Backend caps any single recall() call at ~25s (returns a graceful "busy" answer
// on LLM rate-limit instead of hanging). Some endpoints chain 2+ recall calls, so
// give those headroom before we give up client-side with a friendly message.
const REQUEST_TIMEOUT_MS = 60_000;

async function withTimeout(path, fetchPromiseFactory) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const r = await fetchPromiseFactory(controller.signal);
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return await r.json();
  } catch (e) {
    if (e.name === "AbortError") {
      throw new Error("The knowledge graph is taking longer than usual (LLM provider may be rate-limited). Please try again in a moment.");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function get(path) {
  return withTimeout(path, (signal) => fetch(`${BASE}${path}`, { signal }));
}

async function post(path, body) {
  return withTimeout(path, (signal) =>
    fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    })
  );
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
