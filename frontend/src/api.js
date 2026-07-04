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
async function patch(path, body) {
  const r = await fetch(`${BASE}${path}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json(); if (!r.ok) throw new Error(data.detail || `${path} -> ${r.status}`); return data;
}

export const api = {
  cases: () => get("/cases"),
  createCase: (payload) => post("/cases", payload),
  caseDetail: (caseId) => get(`/cases/${caseId}`),
  caseEvidence: (caseId) => get(`/cases/${caseId}/evidence`),
  caseEventsUrl: (caseId) => `${BASE}/cases/${caseId}/events`,
  uploadCaseEvidence: (caseId, files, contexts) => {
    const fd = new FormData();
    files.forEach((file) => fd.append("files", file));
    fd.append("contexts", JSON.stringify(contexts));
    return fetch(`${BASE}/cases/${caseId}/evidence`, { method: "POST", body: fd }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Upload failed (${r.status})`);
      return data;
    });
  },
  confirmCaseEvidence: (caseId, evidenceId, reviewed_text, context) =>
    post(`/cases/${caseId}/evidence/${evidenceId}/confirm`, { reviewed_text, context }),
  saveEvidenceDraft: (caseId, evidenceId, reviewed_text, context, expected_updated_at) =>
    patch(`/cases/${caseId}/evidence/${evidenceId}/draft`, { reviewed_text, context, expected_updated_at }),
  archiveCase: (caseId) => post(`/cases/${caseId}/archive`, {}),
  restoreCase: (caseId) => post(`/cases/${caseId}/restore`, {}),
  deleteCase: (caseId) => fetch(`${BASE}/cases/${caseId}`, { method: "DELETE" }).then((r) => { if (!r.ok) throw new Error(`Delete failed (${r.status})`); }),
  retryCaseEvidence: (caseId, evidenceId) => post(`/cases/${caseId}/evidence/${evidenceId}/retry`, {}),
  cancelCaseEvidence: (caseId, evidenceId) => post(`/cases/${caseId}/evidence/${evidenceId}/cancel`, {}),
  health: () => get("/health"),
  stats: () => get("/stats"),
  graph: (caseId) => get(caseId ? `/cases/${caseId}/graph` : "/graph"),
  reindexCase: (caseId) => post(`/cases/${caseId}/reindex`, {}),
  caseStats: (caseId) => get(`/cases/${caseId}/stats`),
  caseTimeline: (caseId) => get(`/cases/${caseId}/timeline`),
  caseInterrogation: (caseId, suspect_id) => post(`/cases/${caseId}/interrogation`, { suspect_id, focus_case: caseId }),
  caseWhatIf: (caseId, hypothesis) => post(`/cases/${caseId}/whatif`, { hypothesis, inject_edge: {} }),
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
    return fetch(`${BASE}/ingest-file`, { method: "POST", body: fd }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Upload failed (${r.status})`);
      return data;
    });
  },
  analyzeFile: (file, context = "") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("context", context);
    return fetch(`${BASE}/ingest-file/analyze`, { method: "POST", body: fd }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Analysis failed (${r.status})`);
      return data;
    });
  },
  analyzeFiles: (files, contexts) => {
    const fd = new FormData();
    files.forEach((file) => fd.append("files", file));
    fd.append("contexts", JSON.stringify(contexts));
    return fetch(`${BASE}/ingest-files/analyze`, { method: "POST", body: fd }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Batch analysis failed (${r.status})`);
      return data;
    });
  },
  confirmFile: (review_id, extracted_text, context) =>
    post("/ingest-file/confirm", { review_id, extracted_text, context }),
  confirmFiles: (items) => post("/ingest-files/confirm", { items }),
  transcribe: (blob, filename = "recording.webm") => {
    const fd = new FormData();
    fd.append("file", blob, filename);
    return fetch(`${BASE}/transcribe`, { method: "POST", body: fd }).then((r) => r.json());
  },
  chat: (message, history, caseId) => post(caseId ? `/cases/${caseId}/chat` : "/chat", { message, history }),
  chatSuggestions: (caseId) => get(caseId ? `/cases/${caseId}/chat/suggestions` : "/chat/suggestions"),
  report: () => get("/report"),
  suspectTimeline: (suspect = "daniel-marsh") => get(`/suspect-timeline?suspect=${encodeURIComponent(suspect)}`),
};
