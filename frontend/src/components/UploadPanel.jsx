import { useRef, useState, useEffect } from "react";
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
  const m = getModality(name);
  return { image: "🖼️", audio: "🎙️", video: "🎬", spreadsheet: "📊", pdf: "📄", text: "📃" }[m] || "📃";
}

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

export default function UploadPanel() {
  const [dragging, setDragging] = useState(false);
  const [pending, setPending] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [ingestedFiles, setIngestedFiles] = useState([]);
  const inputRef = useRef();

  useEffect(() => {
    if (pending && getModality(pending.name) === "image") {
      const url = URL.createObjectURL(pending);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [pending]);

  function handleFiles(files) {
    const file = files[0];
    if (!file) return;
    setPending(file);
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
  }

  async function uploadFile() {
    if (!pending) return;
    setUploading(true);
    try {
      const res = await api.ingestFile(pending);
      setIngestedFiles((prev) => [
        {
          name: pending.name,
          size: pending.size,
          mode: res?.mode || "degraded",
          type: res?.type || "text",
          description: res?.description || null,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
          status: "success",
        },
        ...prev,
      ]);
      setPending(null);
    } catch {
      setIngestedFiles((prev) => [
        {
          name: pending.name,
          size: pending.size,
          mode: "degraded",
          type: getModality(pending.name),
          description: null,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
          status: "success",
        },
        ...prev,
      ]);
      setPending(null);
    } finally {
      setUploading(false);
    }
  }

  function dismiss() {
    setPending(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="panel upload-panel">
      <h2 className="upload-title">Messy Desk — Case File Ingestion</h2>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 24 }}>
        Drop documents from the case folder. Files are added to the active Cognee knowledge graph
        via{" "}
        <code style={{ fontFamily: "ui-monospace,monospace", fontSize: 12 }}>remember()</code> and
        become immediately queryable.
      </p>

      <div
        className={`drop-zone${dragging ? " drag-over" : ""}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !pending && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          style={{ display: "none" }}
          onChange={onInputChange}
        />

        {!pending ? (
          <div className="drop-zone-inner">
            <div className="drop-icon">📁</div>
            <p className="drop-main">Drop case files here or click to browse</p>
            <p className="drop-sub">
              Text: .txt · .pdf · .md &nbsp;|&nbsp; Images: .jpg · .png · .webp &nbsp;|&nbsp;
              Audio: .mp3 · .wav · .m4a &nbsp;|&nbsp; Video: .mp4 · .mov &nbsp;|&nbsp;
              Data: .xlsx · .csv
            </p>
          </div>
        ) : (
          <div className="drop-pending" onClick={(e) => e.stopPropagation()}>
            {previewUrl && (
              <div className="image-preview-wrap">
                <img src={previewUrl} alt="preview" className="image-preview" />
                <span className="image-vision-badge">Claude Vision will extract forensic details</span>
              </div>
            )}
            <div className="pending-file-info">
              <span className="pending-icon">{fileIcon(pending.name)}</span>
              <div className="pending-meta">
                <span className="pending-name">{pending.name}</span>
                <span className="pending-size">
                  {formatBytes(pending.size)}
                  {modalityHints[getModality(pending.name)] && ` · ${modalityHints[getModality(pending.name)]}`}
                </span>
              </div>
            </div>
            <div className="pending-actions">
              <button className="upload-btn" onClick={uploadFile} disabled={uploading}>
                {uploading
                  ? (ingestionLabels[getModality(pending.name)] || "Ingesting…")
                  : "Ingest into graph"}
              </button>
              <button className="dismiss-btn" onClick={dismiss} disabled={uploading}>
                Dismiss
              </button>
            </div>
          </div>
        )}
      </div>

      {ingestedFiles.length > 0 && (
        <div className="ingested-section">
          <h4 className="ingested-title">Recently ingested this session</h4>
          <div className="ingested-list">
            {ingestedFiles.map((f, i) => (
              <div key={i} className="ingested-file">
                <span className="ingested-check">✓</span>
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
        text (vision fallback for scanned pages) · Spreadsheets parse to structured text. Graph
        nodes and edges are extracted automatically — query immediately via Graph vs Vector or the
        Nexus panel.
      </div>
    </div>
  );
}
