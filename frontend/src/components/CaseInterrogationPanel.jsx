import { useState } from "react";
import { api } from "../api.js";

export default function CaseInterrogationPanel({ caseId }) {
  const [subject, setSubject] = useState(""); const [result, setResult] = useState(null); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  async function run() { if (!subject.trim()) return; setLoading(true); setError(""); try { setResult(await api.caseInterrogation(caseId, subject.trim())); } catch(e) { setError(e.message); } finally { setLoading(false); } }
  return <div className="panel interrogation-panel"><h2>Interrogation Co-Pilot</h2><p className="muted-copy">Generate evidence-grounded, non-accusatory interview questions from this case only.</p>
    <div className="whatif-input-section"><input className="chat-input" value={subject} onChange={(e)=>setSubject(e.target.value)} placeholder="Person or topic to interview" /><button className="next-btn" onClick={run} disabled={loading || !subject.trim()}>{loading ? "Reviewing case graph…" : "Generate interview strategy"}</button></div>
    {error && <div className="upload-error">{error}</div>}{result && <div className="strategy-box"><span className="strategy-label">Case-scoped strategy</span><p className="strategy-text">{result.narrative}</p><span className={`ingested-mode-badge ${result.mode}`}>{result.mode} mode</span></div>}
  </div>;
}
