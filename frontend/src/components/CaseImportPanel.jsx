import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";

const ACCEPTED = ".txt,.pdf,.md,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.avi,.webm,.xlsx,.xls,.csv";
const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "gif", "webp"]);
const AUDIO_EXTS = new Set(["mp3", "wav", "m4a", "ogg", "aac"]);
const VIDEO_EXTS = new Set(["mp4", "mov", "avi", "webm"]);
const SPREADSHEET_EXTS = new Set(["xlsx", "xls", "csv"]);

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getModality(filename) {
  const ext = (filename || "").split(".").pop().toLowerCase();
  if (IMAGE_EXTS.has(ext)) return "image";
  if (AUDIO_EXTS.has(ext)) return "audio";
  if (VIDEO_EXTS.has(ext)) return "video";
  if (SPREADSHEET_EXTS.has(ext)) return "spreadsheet";
  if (ext === "pdf") return "pdf";
  return "text";
}

function fileIcon(name) {
  return { image: "🖼️", audio: "🎙️", video: "🎬", spreadsheet: "📊", pdf: "📄", text: "📃" }[getModality(name)];
}

// Staged, not-yet-uploaded local files — one card per file with its own
// optional context box, matching the original batch-upload feel.
function newStagedItem(file) {
  return { id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`, file, modality: getModality(file.name), context: "" };
}

export default function CaseImportPanel({ caseId, onGraphUpdated, onNext }) {
  const [data, setData] = useState({ evidence: [], jobs: [] });
  const [staged, setStaged] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [confirmingAll, setConfirmingAll] = useState(false);
  const [notice, setNotice] = useState("");
  const [samples, setSamples] = useState([]);
  const [seeding, setSeeding] = useState(null);
  const [expanded, setExpanded] = useState({});
  const inputRef = useRef();
  const draftTimers = useRef({});
  const sseConnectedRef = useRef(false);

  useEffect(() => { api.sampleCases().then((r) => setSamples(r.sample_cases || [])).catch(() => {}); }, []);

  async function seedSample(sample) {
    setSeeding(sample.id); setError(""); setNotice("");
    try {
      const result = await api.seedSampleCase(caseId, sample.id);
      setNotice(`Loaded "${sample.label}" — ${result.results.length} sample file${result.results.length === 1 ? "" : "s"} queued for analysis.`);
      await refresh();
    } catch (e) { setError(e.message); } finally { setSeeding(null); }
  }

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
  useEffect(() => { refresh(); const timer = setInterval(() => { if (!sseConnectedRef.current) refresh(); }, 1500); return () => clearInterval(timer); }, [caseId]);
  useEffect(() => {
    sseConnectedRef.current = false;
    const events = new EventSource(api.caseEventsUrl(caseId));
    events.onopen = () => { sseConnectedRef.current = true; };
    events.addEventListener("jobs", () => refresh());
    events.onerror = () => { sseConnectedRef.current = false; /* polling above resumes during reconnects */ };
    return () => { events.close(); sseConnectedRef.current = false; };
  }, [caseId]);
  useEffect(() => () => Object.values(draftTimers.current).forEach(clearTimeout), []);
  const latestJobs = useMemo(() => Object.fromEntries(data.jobs.map((job) => [job.evidence_id, job]).reverse()), [data.jobs]);

  const activeJobs = data.jobs.filter((job) => ["queued", "running"].includes(job.status));
  const reviewCount = data.evidence.filter((item) => item.status === "awaiting_review").length;
  const ingestedFiles = useMemo(
    () => data.evidence.filter((item) => item.status === "ingested").sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || "")),
    [data.evidence]
  );

  function addFiles(fileList) {
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;
    setStaged((current) => {
      const signatures = new Set(current.map(({ file }) => `${file.name}:${file.size}:${file.lastModified}`));
      return [...current, ...incoming.filter((file) => {
        const signature = `${file.name}:${file.size}:${file.lastModified}`;
        if (signatures.has(signature)) return false;
        signatures.add(signature);
        return true;
      }).map(newStagedItem)];
    });
    if (inputRef.current) inputRef.current.value = "";
  }
  function patchStaged(id, patch) { setStaged((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item)); }
  function removeStaged(id) { setStaged((current) => current.filter((item) => item.id !== id)); }

  async function analyzeBatch() {
    if (!staged.length) return; setUploading(true); setError("");
    try {
      const files = staged.map((item) => item.file);
      const contexts = staged.map((item) => item.context.trim());
      const result = await api.uploadCaseEvidence(caseId, files, contexts);
      const duplicates = result.results.filter((x) => x.duplicate_skipped).length;
      setNotice(duplicates ? `${duplicates} duplicate file${duplicates === 1 ? " was" : "s were"} skipped.` : `${result.results.length} file${result.results.length === 1 ? "" : "s"} queued for analysis.`);
      setStaged([]);
      await refresh();
    } catch (e) { setError(e.message); } finally { setUploading(false); }
  }

  async function confirmAllReviewed() {
    const candidates = data.evidence.filter((item) => item.status === "awaiting_review");
    if (!candidates.length) return;
    setConfirmingAll(true); setError("");
    let failures = 0;
    for (const item of candidates) {
      try { await api.confirmCaseEvidence(caseId, item.id, drafts[item.id] || item.reviewed_text || item.model_output || "", item.context || ""); }
      catch { failures += 1; }
    }
    await refresh();
    setNotice(failures ? `Confirmed ${candidates.length - failures} file(s); ${failures} failed and remain in review.` : `Confirmed and ingested ${candidates.length} file${candidates.length === 1 ? "" : "s"}.`);
    setConfirmingAll(false);
  }

  function editDraft(item, value) {
    setDrafts((current) => ({ ...current, [item.id]: value }));
    clearTimeout(draftTimers.current[item.id]);
    draftTimers.current[item.id] = setTimeout(() => {
      api.saveEvidenceDraft(caseId, item.id, value, item.context || "", item.updated_at)
        .then((saved) => setData((current) => ({ ...current, evidence: current.evidence.map((entry) => entry.id === saved.id ? saved : entry) })))
        .catch((e) => setError(`Draft save failed: ${e.message}`));
    }, 500);
  }

  return <div className="panel upload-panel durable-import">
    <h2 className="upload-title">Import Case Files and Data</h2>
    <p className="muted-copy" style={{ marginBottom: 24 }}>Drop an entire evidence set. Each file is analyzed independently, reviewed by you, then added to Cognee only after confirmation. Jobs belong to this case and continue if you reload or close this page.</p>

    <div className={`drop-zone batch-drop-zone${dragging ? " drag-over" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}>
      <input ref={inputRef} hidden multiple type="file" accept={ACCEPTED} onChange={(e) => addFiles(e.target.files)} />
      <div className="drop-zone-inner"><div className="drop-icon">📁</div><p className="drop-main">Drop multiple case files here or click to browse</p><p className="drop-sub">Text, PDF, images, audio, video, Excel, and CSV · duplicate selections are ignored</p></div>
    </div>

    {samples.length > 0 && <div className="sample-case-panel">
      <p className="muted-copy">No files of your own yet? Load a ready-made sample case to try the app.</p>
      <div className="sample-case-grid">{samples.map((sample) => <button key={sample.id} type="button" className="sample-case-card" disabled={seeding !== null} onClick={() => seedSample(sample)}>
        <strong>{sample.label}</strong><span>{sample.description}</span><span className="sample-case-count">{seeding === sample.id ? "Loading…" : `${sample.file_count} files`}</span>
      </button>)}</div>
    </div>}

    {staged.length > 0 && <div className="batch-queue">
      <div className="batch-toolbar">
        <strong>{staged.length} file{staged.length === 1 ? "" : "s"} ready</strong>
        <button className="dismiss-btn" disabled={uploading} onClick={() => setStaged([])}>Clear</button>
      </div>
      {staged.map((item) => <div className="batch-file-card" key={item.id}>
        <div className="batch-file-header">
          <span className="pending-icon">{fileIcon(item.file.name)}</span>
          <div className="pending-meta"><span className="pending-name">{item.file.name}</span><span className="pending-size">{formatBytes(item.file.size)} · {item.modality}</span></div>
          <button className="batch-remove" disabled={uploading} onClick={() => removeStaged(item.id)} aria-label={`Remove ${item.file.name}`}>×</button>
        </div>
        {item.modality !== "text" && <div className="evidence-context-block">
          <label htmlFor={`ctx-${item.id}`}>Additional context <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span></label>
          <textarea id={`ctx-${item.id}`} rows={2} value={item.context} disabled={uploading} onChange={(e) => patchStaged(item.id, { context: e.target.value })} placeholder="Who or what is featured, and what is happening?" />
        </div>}
      </div>)}
      <div className="batch-actions"><button className="upload-btn" disabled={uploading} onClick={analyzeBatch}>{uploading ? "Saving…" : `Analyze ${staged.length} file${staged.length === 1 ? "" : "s"}`}</button></div>
    </div>}

    {error && <div className="upload-error">{error}</div>}
    {notice && <div className="upload-note">{notice}</div>}

    {activeJobs.length > 0 && <div className="batch-progress-banner" role="status" aria-live="polite">
      <span className="batch-spinner" aria-hidden="true" />
      <div><strong>{activeJobs.length} file{activeJobs.length === 1 ? "" : "s"} in progress</strong><span>Please keep this page open. Completed files are saved as they finish.</span></div>
    </div>}

    {reviewCount > 0 && <div className="batch-actions batch-actions-top">
      <span className="muted-copy">{reviewCount} file{reviewCount === 1 ? "" : "s"} extracted and ready. Review any of them below if you want, or just confirm.</span>
      <button className="next-btn" disabled={confirmingAll} onClick={confirmAllReviewed}>{confirmingAll ? "Cognifying…" : `Confirm and ingest ${reviewCount} file${reviewCount === 1 ? "" : "s"}`}</button>
    </div>}

    <div className="durable-evidence-list">{data.evidence.filter((item) => item.status !== "ingested").map((item) => { const job = latestJobs[item.id]; return <div className={`batch-file-card status-${item.status}`} key={item.id}>
      <div className="batch-file-header">
        <span className="pending-icon">{fileIcon(item.original_filename)}</span>
        <div className="pending-meta"><strong>{item.original_filename}</strong><span className="pending-size">{item.modality} · {item.status.replaceAll("_", " ")}</span></div>
        <span className="batch-status">{item.status.replaceAll("_", " ")}</span>
      </div>
      {job && ["queued", "running"].includes(job.status) && <div className="file-progress-wrap">
        <div className="file-progress-label"><span>{job.stage.replaceAll("_", " ")}</span><span>{job.progress}%</span></div>
        <div className="file-progress-track" role="progressbar" aria-valuenow={job.progress} aria-valuemin="0" aria-valuemax="100"><div className="file-progress-fill" style={{ width: `${job.progress}%` }} /></div>
      </div>}
      {item.status === "awaiting_review" && <div className="evidence-review-block">
        <button type="button" className="evidence-review-toggle" onClick={() => setExpanded((current) => ({ ...current, [item.id]: !current[item.id] }))}>
          {expanded[item.id] ? "▾ Hide extracted text" : "▸ Review / edit extracted text (optional)"}
        </button>
        {expanded[item.id] && <>
          <p>Edit inaccuracies or omissions. This confirmed text is what Cognee receives.</p>
          <textarea rows={9} value={drafts[item.id] || ""} onChange={(e) => editDraft(item, e.target.value)} />
          <small style={{ color: "var(--muted)" }}>Draft saves automatically. Use "Confirm and ingest" above once you're done reviewing.</small>
        </>}
      </div>}
      {["analysis_failed", "ingestion_failed"].includes(item.status) && <div><div className="upload-error">{item.error_message}</div><button className="upload-btn" onClick={() => api.retryCaseEvidence(caseId, item.id).then(refresh)}>Retry</button></div>}
      {["queued_analysis", "analyzing", "queued_ingestion", "ingesting"].includes(item.status) && <button className="dismiss-btn" onClick={() => api.cancelCaseEvidence(caseId, item.id).then(refresh)}>Cancel</button>}
    </div>; })}</div>

    {ingestedFiles.length > 0 && <div className="ingested-section">
      <h4 className="ingested-title">Recently ingested this session</h4>
      <div className="ingested-list">{ingestedFiles.map((item) => <div key={item.id} className="ingested-file">
        <span className="ingested-check">✓</span>
        <div className="ingested-info" style={{ flex: 1 }}><span className="ingested-name">{item.original_filename}</span><span className="ingested-detail">{formatBytes(item.size_bytes)} · {item.modality} · verified</span></div>
      </div>)}</div>
    </div>}

    <div className="upload-note">Analysis runs on this case's durable job queue, so it survives reloads. Confirmation is serialized to protect Cognee's embedded graph writer. Failed files remain in the queue for correction or retry.</div>
    {ingestedFiles.length > 0 && onNext && <div className="upload-next-row"><button className="next-btn" onClick={() => { onGraphUpdated?.(); onNext?.(); }}>Continue to Evidence Board</button></div>}
  </div>;
}
