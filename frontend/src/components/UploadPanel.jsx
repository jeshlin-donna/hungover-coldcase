import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const ACCEPTED = ".txt,.pdf,.md,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.avi,.webm,.xlsx,.xls,.csv";
const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "gif", "webp"]);
const AUDIO_EXTS = new Set(["mp3", "wav", "m4a", "ogg", "aac"]);
const VIDEO_EXTS = new Set(["mp4", "mov", "avi", "webm"]);
const SPREADSHEET_EXTS = new Set(["xlsx", "xls", "csv"]);

function formatBytes(bytes) {
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

function ImagePreview({ file }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url ? <img src={url} alt={`Preview of ${file.name}`} className="batch-image-preview" /> : null;
}

function newItem(file) {
  return {
    id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`,
    file,
    modality: getModality(file.name),
    context: "",
    reviewId: null,
    reviewText: "",
    status: "pending",
    progress: 0,
    error: "",
  };
}

export default function UploadPanel({ onGraphUpdated, onNext }) {
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState([]);
  const [ingestedFiles, setIngestedFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [batchPhase, setBatchPhase] = useState("");
  const inputRef = useRef();

  useEffect(() => {
    if (!busy) return undefined;
    const timer = window.setInterval(() => {
      setItems((current) => current.map((item) => {
        if (item.status !== "analyzing" && item.status !== "confirming") return item;
        const ceiling = item.status === "analyzing" ? 88 : 92;
        const increment = item.progress < 35 ? 7 : item.progress < 70 ? 3 : 1;
        return { ...item, progress: Math.min(ceiling, item.progress + increment) };
      }));
    }, 650);
    return () => window.clearInterval(timer);
  }, [busy]);

  function addFiles(fileList) {
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;
    setItems((current) => {
      const signatures = new Set(current.map(({ file }) => `${file.name}:${file.size}:${file.lastModified}`));
      return [...current, ...incoming.filter((file) => {
        const signature = `${file.name}:${file.size}:${file.lastModified}`;
        if (signatures.has(signature)) return false;
        signatures.add(signature);
        return true;
      }).map(newItem)];
    });
    if (inputRef.current) inputRef.current.value = "";
  }

  function patchItem(id, patch) {
    setItems((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item));
  }

  function removeItem(id) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  async function analyzeBatch() {
    const candidates = items.filter((item) => item.status === "pending" || item.status === "error");
    if (!candidates.length) return;
    const eligible = [];
    eligible.push(...candidates);
    if (!eligible.length) return;
    setBusy(true);
    setBatchPhase("Analyzing evidence");
    setItems((current) => current.map((item) =>
      eligible.some(({ id }) => id === item.id) ? { ...item, status: "queued", progress: 0, error: "" } : item
    ));
    try {
      let cursor = 0;
      async function worker() {
        while (cursor < eligible.length) {
          const item = eligible[cursor++];
          try {
            patchItem(item.id, { status: "analyzing", progress: 5 });
            const result = await api.analyzeFile(item.file, item.context.trim());
            patchItem(item.id, { status: "reviewing", progress: 100,
              reviewId: result.review_id, reviewText: result.extracted_text || "", error: "" });
          } catch (error) {
            patchItem(item.id, { status: "error", progress: 0,
              error: error.message || "Analysis failed." });
          }
        }
      }
      await Promise.all(Array.from({ length: Math.min(3, eligible.length) }, worker));
    } finally {
      setBusy(false);
      setBatchPhase("");
    }
  }

  async function confirmBatch() {
    const candidates = items.filter((item) => item.status === "reviewing");
    if (!candidates.length) return;
    const valid = candidates.filter((item) => item.reviewText.trim());
    candidates.filter((item) => !item.reviewText.trim()).forEach((item) =>
      patchItem(item.id, { error: "Reviewed evidence cannot be empty." })
    );
    if (!valid.length) return;
    setBusy(true);
    setBatchPhase("Adding verified evidence to the knowledge graph");
    setItems((current) => current.map((item) =>
      valid.some(({ id }) => id === item.id) ? { ...item, status: "queued", progress: 0, error: "" } : item
    ));
    try {
      let successCount = 0;
      for (const item of valid) {
        patchItem(item.id, { status: "confirming", progress: 5 });
        try {
          const result = await api.confirmFile(item.reviewId, item.reviewText, item.context.trim());
          patchItem(item.id, { status: "complete", progress: 100 });
          setIngestedFiles((current) => [{ name: item.file.name, size: item.file.size,
            type: item.modality, mode: result.mode || "degraded",
            timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) }, ...current]);
          await new Promise((resolve) => window.setTimeout(resolve, 350));
          removeItem(item.id);
          successCount += 1;
        } catch (error) {
          patchItem(item.id, { status: "reviewing", progress: 0,
            error: error.message || "Ingestion failed. Review and retry this file." });
        }
      }
      if (successCount) onGraphUpdated?.();
    } finally {
      setBusy(false);
      setBatchPhase("");
    }
  }

  const reviewCount = items.filter((item) => item.status === "reviewing").length;
  const pendingCount = items.filter((item) => item.status === "pending" || item.status === "error").length;

  return (
    <div className="panel upload-panel">
      <h2 className="upload-title">Import Case Files and Data</h2>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 24 }}>
        Drop an entire evidence set. Each file is analyzed independently, reviewed by you, then
        added to Cognee only after confirmation.
      </p>

      <div className={`drop-zone batch-drop-zone${dragging ? " drag-over" : ""}`}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" multiple accept={ACCEPTED} style={{ display: "none" }}
          onChange={(event) => addFiles(event.target.files)} />
        <div className="drop-zone-inner">
          <div className="drop-icon">📁</div>
          <p className="drop-main">Drop multiple case files here or click to browse</p>
          <p className="drop-sub">Text, PDF, images, audio, video, Excel, and CSV · duplicate selections are ignored</p>
        </div>
      </div>

      {items.length > 0 && (
        <div className="batch-queue">
          {busy && (
            <div className="batch-progress-banner" role="status" aria-live="polite">
              <span className="batch-spinner" aria-hidden="true" />
              <div><strong>{batchPhase}</strong><span>Please keep this page open. Completed files are saved as they finish.</span></div>
            </div>
          )}
          <div className="batch-toolbar">
            <strong>{items.length} file{items.length === 1 ? "" : "s"} in this batch</strong>
            <button className="dismiss-btn" disabled={busy} onClick={() => setItems([])}>Clear batch</button>
          </div>
          {items.map((item) => (
            <div className={`batch-file-card status-${item.status}`} key={item.id}>
              <div className="batch-file-header">
                <span className="pending-icon">{fileIcon(item.file.name)}</span>
                <div className="pending-meta">
                  <span className="pending-name">{item.file.name}</span>
                  <span className="pending-size">{formatBytes(item.file.size)} · {item.modality}</span>
                </div>
                <span className="batch-status">{item.status}</span>
                <button className="batch-remove" disabled={busy} onClick={() => removeItem(item.id)} aria-label={`Remove ${item.file.name}`}>×</button>
              </div>
              {(item.status === "analyzing" || item.status === "queued" || item.status === "confirming" || item.status === "complete") && (
                <div className="file-progress-wrap">
                  <div className="file-progress-label">
                    <span>{item.status === "analyzing" ? "Extracting and analyzing" : item.status === "queued" ? "Waiting for its turn" : item.status === "complete" ? "Ingested" : "Cognifying and updating graph"}</span>
                    <span>{item.progress}%</span>
                  </div>
                  <div className="file-progress-track" role="progressbar" aria-valuenow={item.progress} aria-valuemin="0" aria-valuemax="100">
                    <div className="file-progress-fill" style={{ width: `${item.progress}%` }} />
                  </div>
                </div>
              )}
              {item.modality === "image" && <ImagePreview file={item.file} />}
              {item.modality !== "text" && !item.reviewId && (
                <div className="evidence-context-block">
                  <label htmlFor={`context-${item.id}`}>Additional context <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span></label>
                  <p>Add people, situation, source, date, location, or details that could improve the model's analysis.</p>
                  <textarea id={`context-${item.id}`} rows={3} value={item.context} disabled={busy}
                    onChange={(event) => patchItem(item.id, { context: event.target.value, error: "", status: "pending" })}
                    placeholder="Who or what is featured, and what is happening?" />
                </div>
              )}
              {item.reviewId && (
                <div className="evidence-review-block">
                  <div className="evidence-review-heading">Verify extracted evidence</div>
                  <p>Edit inaccuracies or omissions. This confirmed text is what Cognee receives.</p>
                  <textarea rows={9} value={item.reviewText} disabled={busy}
                    onChange={(event) => patchItem(item.id, { reviewText: event.target.value, error: "" })} />
                </div>
              )}
              {item.error && <div className="upload-error" role="alert">{item.error}</div>}
            </div>
          ))}
          <div className="batch-actions">
            {pendingCount > 0 && <button className="upload-btn" disabled={busy} onClick={analyzeBatch}>{busy ? "Working…" : `Analyze ${pendingCount} file${pendingCount === 1 ? "" : "s"}`}</button>}
            {reviewCount > 0 && <button className="next-btn" disabled={busy} onClick={confirmBatch}>{busy ? "Cognifying…" : `Confirm and ingest ${reviewCount} reviewed file${reviewCount === 1 ? "" : "s"}`}</button>}
          </div>
        </div>
      )}

      {ingestedFiles.length > 0 && (
        <div className="ingested-section">
          <h4 className="ingested-title">Recently ingested this session</h4>
          <div className="ingested-list">{ingestedFiles.map((file, index) => (
            <div key={`${file.name}-${index}`} className="ingested-file">
              <span className="ingested-check">✓</span>
              <div className="ingested-info" style={{ flex: 1 }}>
                <span className="ingested-name">{file.name}</span>
                <span className="ingested-detail">{formatBytes(file.size)} · {file.timestamp} · verified</span>
              </div>
              <span className={`ingested-mode-badge ${file.mode}`}>{file.mode} mode</span>
            </div>
          ))}</div>
        </div>
      )}

      <div className="upload-note">Batch analysis allows partial success and up to three media extractions at once. Confirmation is serialized to protect Cognee's embedded graph writer. Failed files remain in the queue for correction or retry.</div>
      {ingestedFiles.length > 0 && onNext && <div className="upload-next-row"><button className="next-btn" onClick={onNext}>Continue to Evidence Board</button></div>}
    </div>
  );
}
