import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";

const ACCEPTED = ".txt,.pdf,.md,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.avi,.webm,.xlsx,.xls,.csv";

export default function CaseImportPanel({ caseId, onGraphUpdated, onNext }) {
  const [data, setData] = useState({ evidence: [], jobs: [] });
  const [selected, setSelected] = useState([]);
  const [context, setContext] = useState("");
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  async function refresh() {
    try {
      const next = await api.caseEvidence(caseId); setData(next);
      setDrafts((current) => {
        const copy = { ...current };
        next.evidence.forEach((item) => { if (item.status === "awaiting_review" && copy[item.id] === undefined) copy[item.id] = item.reviewed_text || item.model_output || ""; });
        return copy;
      });
    } catch (e) { setError(e.message); }
  }
  useEffect(() => { refresh(); const timer = setInterval(refresh, 1500); return () => clearInterval(timer); }, [caseId]);
  useEffect(() => {
    const events = new EventSource(api.caseEventsUrl(caseId));
    events.addEventListener("jobs", () => refresh());
    events.onerror = () => { /* polling above remains active during reconnects */ };
    return () => events.close();
  }, [caseId]);
  const latestJobs = useMemo(() => Object.fromEntries(data.jobs.map((job) => [job.evidence_id, job]).reverse()), [data.jobs]);

  async function upload() {
    if (!selected.length) return; setUploading(true); setError("");
    try { await api.uploadCaseEvidence(caseId, selected, selected.map(() => context)); setSelected([]); setContext(""); await refresh(); }
    catch (e) { setError(e.message); } finally { setUploading(false); }
  }
  async function confirm(item) { try { await api.confirmCaseEvidence(caseId, item.id, drafts[item.id], item.context || ""); await refresh(); } catch (e) { setError(e.message); } }

  return <div className="panel upload-panel durable-import">
    <h2>Import Case Files and Data</h2><p className="muted-copy">Jobs belong to this case and continue if you reload or close this page.</p>
    <div className="drop-zone" onClick={() => inputRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setSelected(Array.from(e.dataTransfer.files)); }}>
      <input ref={inputRef} hidden multiple type="file" accept={ACCEPTED} onChange={(e) => setSelected(Array.from(e.target.files))} />
      <div className="drop-zone-inner"><div className="drop-icon">📁</div><p className="drop-main">Drop multiple files or click to browse</p><p className="drop-sub">Files are saved before analysis starts.</p></div>
    </div>
    {selected.length > 0 && <div className="durable-upload-ready"><strong>{selected.length} file{selected.length === 1 ? "" : "s"} ready</strong>
      <textarea rows={3} value={context} onChange={(e) => setContext(e.target.value)} placeholder="Optional context applied to these files" />
      <button className="upload-btn" disabled={uploading} onClick={upload}>{uploading ? "Saving files…" : "Save and analyze"}</button></div>}
    {error && <div className="upload-error">{error}</div>}
    <div className="durable-evidence-list">{data.evidence.map((item) => { const job = latestJobs[item.id]; return <div className="batch-file-card" key={item.id}>
      <div className="batch-file-header"><div className="pending-meta"><strong>{item.original_filename}</strong><span className="pending-size">{item.modality} · {item.status.replaceAll("_", " ")}</span></div><span className="batch-status">{item.status.replaceAll("_", " ")}</span></div>
      {job && ["queued", "running"].includes(job.status) && <div className="file-progress-wrap"><div className="file-progress-label"><span>{job.stage.replaceAll("_", " ")}</span><span>{job.progress}%</span></div><div className="file-progress-track"><div className="file-progress-fill" style={{ width: `${job.progress}%` }} /></div></div>}
      {item.status === "awaiting_review" && <div className="evidence-review-block"><div className="evidence-review-heading">Verify extracted evidence</div><textarea rows={9} value={drafts[item.id] || ""} onChange={(e) => setDrafts({ ...drafts, [item.id]: e.target.value })} /><button className="next-btn" onClick={() => confirm(item)}>Confirm and ingest</button></div>}
      {["analysis_failed", "ingestion_failed"].includes(item.status) && <div><div className="upload-error">{item.error_message}</div><button className="upload-btn" onClick={() => api.retryCaseEvidence(caseId, item.id).then(refresh)}>Retry</button></div>}
      {["queued_analysis", "analyzing", "queued_ingestion", "ingesting"].includes(item.status) && <button className="dismiss-btn" onClick={() => api.cancelCaseEvidence(caseId, item.id).then(refresh)}>Cancel</button>}
    </div>; })}</div>
    {data.evidence.some((item) => item.status === "ingested") && <div className="upload-next-row"><button className="next-btn" onClick={() => { onGraphUpdated?.(); onNext?.(); }}>Continue to Evidence Board</button></div>}
  </div>;
}
