import { useEffect, useState } from "react";
import { api } from "../api.js";

const CASE_SUMMARY_CACHE = "coldcache_case_summaries_v1";

function cachedCases() {
  try { return JSON.parse(localStorage.getItem(CASE_SUMMARY_CACHE) || "[]"); }
  catch { return []; }
}

export default function CaseHome({ onOpen }) {
  const [cases, setCases] = useState(cachedCases);
  const [loading, setLoading] = useState(true);
  const [usingCache, setUsingCache] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", reference_number: "", jurisdiction: "", description: "" });
  const [error, setError] = useState("");

  async function load() {
    try {
      const serverCases = (await api.cases()).cases || [];
      setCases(serverCases); setError(""); setUsingCache(false);
      try { localStorage.setItem(CASE_SUMMARY_CACHE, JSON.stringify(serverCases)); } catch { /* storage optional */ }
    } catch (e) {
      setError("Case database is temporarily unavailable. Reconnecting…");
      setUsingCache(cachedCases().length > 0 || cases.length > 0);
    } finally { setLoading(false); }
  }
  useEffect(() => {
    load();
    const retry = setInterval(() => { if (document.visibilityState === "visible") load(); }, 2500);
    return () => clearInterval(retry);
  }, []);

  async function create(event) {
    event.preventDefault(); setError("");
    try {
      const created = await api.createCase(form);
      onOpen(created);
    } catch (e) { setError(e.message || "Could not create case."); }
  }
  async function archive(event, item) { event.stopPropagation(); await (item.status === "archived" ? api.restoreCase(item.id) : api.archiveCase(item.id)); load(); }
  async function remove(event, item) { event.stopPropagation(); if (!window.confirm(`Delete case "${item.title}" and its stored evidence?`)) return; try { await api.deleteCase(item.id); load(); } catch (e) { setError(e.message); } }

  return <div className="case-home">
    <div className="case-home-header"><div><div className="header-logo">🔍</div><h1>ColdCache</h1><p>Case memory that survives the browser.</p></div>
      <button className="next-btn" onClick={() => setCreating(true)}>Create case</button></div>
    {error && <div className={usingCache ? "upload-note" : "upload-error"}>{error}{usingCache ? " Showing the last known case list." : ""}</div>}
    {loading && cases.length === 0 && <div className="case-empty"><span className="batch-spinner" /><h2>Loading cases…</h2><p>Connecting to the persistent case database.</p></div>}
    {!loading && !error && !creating && cases.length === 0 && <div className="case-empty">
      <div className="case-empty-icon">📂</div><h2>No cases yet</h2>
      <p>Create a case before importing evidence. Files, reviews, analysis jobs, and the knowledge graph will stay isolated to it.</p>
      <button className="upload-btn" onClick={() => setCreating(true)}>Create your first case</button>
    </div>}
    {creating && <form className="case-create-form" onSubmit={create}>
      <div className="row"><div><h2>Create case</h2><p>Only the title is required. You can add details later.</p></div><button type="button" className="dismiss-btn" onClick={() => setCreating(false)}>Cancel</button></div>
      <label>Case title *<input autoFocus required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Oak Street burglary series" /></label>
      <div className="case-form-grid"><label>Reference number<input value={form.reference_number} onChange={(e) => setForm({ ...form, reference_number: e.target.value })} placeholder="CC-2026-014" /></label>
      <label>Jurisdiction<input value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })} placeholder="Maple Heights PD" /></label></div>
      <label>Description<textarea rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Brief case context…" /></label>
      <button className="next-btn" type="submit" disabled={!form.title.trim()}>Create and open case</button>
    </form>}
    {!creating && cases.length > 0 && <div className="case-grid">{cases.map((item) =>
      <div className="case-card" role="button" tabIndex="0" key={item.id} onClick={() => onOpen(item)} onKeyDown={(e) => { if (e.key === "Enter") onOpen(item); }}>
        <span className="case-card-status">{item.status}</span><h3>{item.title}</h3>
        <p>{item.reference_number || item.jurisdiction || "No reference details"}</p>
        <div><span>{item.evidence_count || 0} evidence</span><span>{item.active_jobs || 0} active jobs</span></div>
        <div style={{marginTop:12}}><button type="button" className="dismiss-btn" onClick={(e) => archive(e,item)}>{item.status === "archived" ? "Restore" : "Archive"}</button><button type="button" className="dismiss-btn" onClick={(e) => remove(e,item)}>Delete</button></div>
      </div>)}</div>}
  </div>;
}
