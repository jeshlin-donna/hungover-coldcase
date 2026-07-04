import { useRef, useState, useEffect } from "react";
import JSZip from "jszip";
import { api } from "../api.js";

const ACCEPTED =
  ".txt,.pdf,.md,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.avi,.webm,.xlsx,.xls,.csv,.zip";
const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "gif", "webp"]);
const AUDIO_EXTS = new Set(["mp3", "wav", "m4a", "ogg", "aac"]);
const VIDEO_EXTS = new Set(["mp4", "mov", "avi", "webm"]);
const SPREADSHEET_EXTS = new Set(["xlsx", "xls", "csv"]);
const IGNORE_NAMES = new Set([".ds_store", "thumbs.db", "desktop.ini"]);

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function extOf(filename) {
  return (filename || "").split(".").pop().toLowerCase();
}

function getModality(filename) {
  const ext = extOf(filename);
  if (IMAGE_EXTS.has(ext)) return "image";
  if (AUDIO_EXTS.has(ext)) return "audio";
  if (VIDEO_EXTS.has(ext)) return "video";
  if (SPREADSHEET_EXTS.has(ext)) return "spreadsheet";
  if (ext === "pdf") return "pdf";
  return "text";
}

const fileIcon = (name) =>
  ({ image: "🖼️", audio: "🎙️", video: "🎬", spreadsheet: "📊", pdf: "📄", text: "📃" }[
    getModality(name)
  ] || "📃");

const modalityColor = (name) =>
  ({ image: "#58a6ff", audio: "#e3b341", video: "#f778ba", spreadsheet: "#3fb950", pdf: "#d29922", text: "#8b949e" }[
    getModality(name)
  ] || "#8b949e");

const modalityHints = {
  image: "image → Claude vision → graph",
  audio: "audio → Whisper transcript → graph",
  video: "video → keyframes → Claude vision → graph",
  pdf: "PDF → text/OCR extraction → graph",
  spreadsheet: "spreadsheet → structured text → graph",
  text: "",
};

const ingestionLabels = {
  image: "Analyzing image…",
  audio: "Transcribing audio…",
  video: "Extracting frames…",
  pdf: "Extracting PDF…",
  spreadsheet: "Parsing spreadsheet…",
  text: "Ingesting…",
};

let queueId = 0;

// Expand a drop/pick event's raw files into a flat list of real ingestible
// files, transparently unzipping any .zip archives (client-side, via JSZip)
// so a judge can drag a whole case folder (zipped) in one motion.
async function expandToFiles(rawFiles) {
  const out = [];
  for (const file of rawFiles) {
    const ext = extOf(file.name);
    if (ext === "zip") {
      try {
        const zip = await JSZip.loadAsync(file);
        const entries = Object.values(zip.files).filter((e) => !e.dir);
        for (const entry of entries) {
          const baseName = entry.name.split("/").pop();
          if (!baseName || IGNORE_NAMES.has(baseName.toLowerCase()) || baseName.startsWith(".")) continue;
          const blob = await entry.async("blob");
          out.push(new File([blob], baseName, { type: blob.type }));
        }
      } catch {
        // Not a valid zip / corrupt — skip it rather than crash the drop.
      }
    } else {
      const baseName = file.name.split("/").pop();
      if (IGNORE_NAMES.has(baseName.toLowerCase()) || baseName.startsWith(".")) continue;
      out.push(file);
    }
  }
  return out;
}

export default function UploadPanel({ onGraphUpdated, onNext }) {
  const [dragging, setDragging] = useState(false);
  const [queue, setQueue] = useState([]); // [{id, file, status, description, mode}]
  const [expanding, setExpanding] = useState(false);
  const [ingestedFiles, setIngestedFiles] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const inputRef = useRef();
  const folderInputRef = useRef();
  const processingRef = useRef(false);

  const firstImage = queue.find((q) => q.status === "queued" && getModality(q.file.name) === "image");
  useEffect(() => {
    if (firstImage) {
      const url = URL.createObjectURL(firstImage.file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstImage?.id]);

  async function handleFiles(rawFiles) {
    const list = Array.from(rawFiles || []);
    if (!list.length) return;
    setExpanding(true);
    const expanded = await expandToFiles(list);
    setExpanding(false);
    if (!expanded.length) return;
    setQueue((prev) => [
      ...prev,
      ...expanded.map((file) => ({ id: ++queueId, file, status: "queued" })),
    ]);
  }

  function onDragOver(e) {
    e.preventDefault();
    setDragging(true);
  }
  function onDragLeave() {
    setDragging(false);
  }
  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }
  function onInputChange(e) {
    handleFiles(e.target.files);
    e.target.value = "";
  }

  function removeFromQueue(id) {
    setQueue((prev) => prev.filter((q) => q.id !== id));
  }
  function clearQueue() {
    setQueue([]);
  }

  async function ingestAll() {
    if (processingRef.current) return;
    processingRef.current = true;
    // Sequential on purpose: the backend's LLM-backed extraction is
    // throughput-limited, so a tight upload loop would just queue up
    // rate-limit retries. One at a time keeps status feedback honest.
    const snapshot = queue.filter((q) => q.status === "queued");
    for (const { id, file } of snapshot) {
      setQueue((prev) => prev.map((q) => (q.id === id ? { ...q, status: "uploading" } : q)));
      let result;
      try {
        result = await api.ingestFile(file);
        setQueue((prev) => prev.map((q) => (q.id === id ? { ...q, status: "done" } : q)));
      } catch {
        result = null;
        setQueue((prev) => prev.map((q) => (q.id === id ? { ...q, status: "error" } : q)));
      }
      setIngestedFiles((prev) => [
        {
          name: file.name,
          size: file.size,
          mode: result?.mode || "degraded",
          type: result?.type || getModality(file.name),
          description: result?.description || null,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
          status: result ? "success" : "error",
        },
        ...prev,
      ]);
      onGraphUpdated?.();
      // brief pause so the UI can visibly step through the queue rather than blur past it
      await new Promise((r) => setTimeout(r, 150));
    }
    setQueue((prev) => prev.filter((q) => q.status !== "done"));
    processingRef.current = false;
  }

  const queuedCount = queue.filter((q) => q.status === "queued").length;
  const modalityTally = queue.reduce((acc, q) => {
    const m = getModality(q.file.name);
    acc[m] = (acc[m] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="panel upload-panel">
      <h2 className="upload-title">Messy Desk — Case File Ingestion</h2>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 24 }}>
        Drop documents, a whole case folder, or a zipped case bundle. Every file type is
        auto-detected and flows into the active Cognee knowledge graph via{" "}
        <code style={{ fontFamily: "ui-monospace,monospace", fontSize: 12 }}>remember()</code> —
        instantly queryable.
      </p>

      <div
        className={`drop-zone${dragging ? " drag-over" : ""}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          style={{ display: "none" }}
          onChange={onInputChange}
        />
        <input
          ref={folderInputRef}
          type="file"
          multiple
          webkitdirectory="true"
          directory="true"
          style={{ display: "none" }}
          onChange={onInputChange}
        />

        <div className="drop-zone-inner">
          <div className="drop-icon">{expanding ? "⏳" : "📁"}</div>
          <p className="drop-main">
            {expanding ? "Unpacking archive…" : "Drop case files, a folder, or a .zip here"}
          </p>
          <p className="drop-sub">
            Text: .txt · .pdf · .md &nbsp;|&nbsp; Images: .jpg · .png · .webp &nbsp;|&nbsp;
            Audio: .mp3 · .wav · .m4a &nbsp;|&nbsp; Video: .mp4 · .mov &nbsp;|&nbsp;
            Data: .xlsx · .csv &nbsp;|&nbsp; or a whole <strong>.zip</strong> bundle
          </p>
          <button
            type="button"
            className="folder-pick-btn"
            onClick={(e) => {
              e.stopPropagation();
              folderInputRef.current?.click();
            }}
          >
            📂 Choose a folder…
          </button>
        </div>
      </div>

      {queue.length > 0 && (
        <div className="queue-section">
          <div className="queue-header">
            <h4 className="ingested-title" style={{ margin: 0 }}>
              Ready to ingest ({queue.length})
            </h4>
            <div className="queue-tally">
              {Object.entries(modalityTally).map(([m, n]) => (
                <span key={m} className="tally-chip" style={{ borderColor: modalityColor(m) + "55", color: modalityColor(m) }}>
                  {{ image: "🖼️", audio: "🎙️", video: "🎬", spreadsheet: "📊", pdf: "📄", text: "📃" }[m]} {n}
                </span>
              ))}
            </div>
          </div>

          {previewUrl && (
            <div className="image-preview-wrap">
              <img src={previewUrl} alt="preview" className="image-preview" />
              <span className="image-vision-badge">Claude Vision will extract forensic details</span>
            </div>
          )}

          <div className="queue-list">
            {queue.map((q) => (
              <div key={q.id} className={`queue-item queue-item--${q.status}`} style={{ borderLeftColor: modalityColor(q.file.name) }}>
                <span className="pending-icon">{fileIcon(q.file.name)}</span>
                <div className="pending-meta" style={{ flex: 1, minWidth: 0 }}>
                  <span className="pending-name">{q.file.name}</span>
                  <span className="pending-size">
                    {formatBytes(q.file.size)}
                    {modalityHints[getModality(q.file.name)] && ` · ${modalityHints[getModality(q.file.name)]}`}
                  </span>
                </div>
                {q.status === "queued" && (
                  <button className="dismiss-btn dismiss-btn--sm" onClick={() => removeFromQueue(q.id)}>
                    ✕
                  </button>
                )}
                {q.status === "uploading" && (
                  <span className="queue-spinner">{ingestionLabels[getModality(q.file.name)] || "Ingesting…"}</span>
                )}
                {q.status === "error" && <span className="queue-error">failed</span>}
              </div>
            ))}
          </div>

          <div className="pending-actions" style={{ marginTop: 14 }}>
            <button className="upload-btn" onClick={ingestAll} disabled={queuedCount === 0}>
              Ingest all into graph ({queuedCount})
            </button>
            <button className="dismiss-btn" onClick={clearQueue}>
              Clear queue
            </button>
          </div>
        </div>
      )}

      {ingestedFiles.length > 0 && (
        <div className="ingested-section">
          <h4 className="ingested-title">Recently ingested this session</h4>
          <div className="ingested-list">
            {ingestedFiles.map((f, i) => (
              <div key={i} className="ingested-file" style={{ borderLeftColor: modalityColor(f.name), borderLeftWidth: 3, borderLeftStyle: "solid" }}>
                <span className="ingested-check">{f.status === "error" ? "⚠️" : "✓"}</span>
                <span className="ingested-file-icon">{fileIcon(f.name)}</span>
                <div className="ingested-info" style={{ flex: 1 }}>
                  <span className="ingested-name">{f.name}</span>
                  <span className="ingested-detail">
                    {formatBytes(f.size)} · {f.timestamp}
                    {f.type && f.type !== "text" && ` · ${f.type} extracted`}
                  </span>
                  {f.description && (
                    <div className="image-description-box">
                      <span className="image-description-label">{f.type} extraction:</span>
                      <p className="image-description-text">{f.description}</p>
                    </div>
                  )}
                </div>
                <span className={`ingested-mode-badge ${f.mode}`}>
                  {f.mode === "live" ? "live" : "degraded"} mode
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="upload-note">
        All file types flow into Cognee via{" "}
        <code style={{ fontFamily: "ui-monospace,monospace", fontSize: 12 }}>remember()</code>.
        Images use Claude vision · Audio uses Whisper · Video extracts keyframes · PDFs extract
        text (vision fallback for scanned pages) · Spreadsheets parse to structured text. Drop a
        whole folder or a .zip and every file is auto-detected and routed to the right extractor.
        Graph nodes and edges are extracted automatically — query immediately via Graph vs Vector
        or the Nexus panel.
      </div>

      {ingestedFiles.length > 0 && onNext && (
        <div className="upload-next-row">
          <button className="next-btn" onClick={onNext}>
            Continue to Evidence Board
          </button>
        </div>
      )}

      {onNext && (
        <div className="upload-debug-row">
          <button className="debug-test-btn" onClick={onNext}>
            Next → (testmode)
          </button>
        </div>
      )}
    </div>
  );
}
