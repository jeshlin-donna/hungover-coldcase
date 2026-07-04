import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function CaseHome({ onOpen }) {
  const [cases, setCases] = useState([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", reference_number: "", jurisdiction: "", description: "" });
  const [error, setError] = useState("");

  async function load() {
    try { setCases((await api.cases()).cases || []); } catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function create(event) {
    event.preventDefault(); setError("");
    try {
      const created = await api.createCase(form);
      onOpen(created);
    } catch (e) { setError(e.message || "Could not create case."); }
  }

  return <div className="case-home">
    <div className="case-home-header"><div><div className="header-logo">🔍</div><h1>ColdCache</h1><p>Case memory that survives the browser.</p></div>
      <button className="next-btn" onClick={() => setCreating(true)}>Create case</button></div>
    {error && <div className="upload-error">{error}</div>}
    {!creating && cases.length === 0 && <div className="case-empty">
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
      <button className="case-card" key={item.id} onClick={() => onOpen(item)}>
        <span className="case-card-status">{item.status}</span><h3>{item.title}</h3>
        <p>{item.reference_number || item.jurisdiction || "No reference details"}</p>
        <div><span>{item.evidence_count || 0} evidence</span><span>{item.active_jobs || 0} active jobs</span></div>
      </button>)}</div>}
  </div>;
}
