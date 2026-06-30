import { useRef, useState, useEffect } from "react";
import { api } from "../api.js";

const ACCEPTED = ".txt,.pdf,.md,.jpg,.jpeg,.png,.gif,.webp";
const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "gif", "webp"]);

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function isImage(filename) {
  return IMAGE_EXTS.has((filename || "").split(".").pop().toLowerCase());
}

function fileIcon(name) {
  if (isImage(name)) return "🖼️";
  if (name.endsWith(".pdf")) return "📄";
  if (name.endsWith(".md")) return "📝";
  return "📃";
}

export default function UploadPanel() {
  const [dragging, setDragging] = useState(false);
  const [pending, setPending] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [ingestedFiles, setIngestedFiles] = useState([]);
  const inputRef = useRef();

  useEffect(() => {
    if (pending && isImage(pending.name)) {
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
          imageDescription: res?.image_description || null,
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
          type: isImage(pending.name) ? "image" : "text",
          imageDescription: null,
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
            <p className="drop-main">Drop case files or images here or click to browse</p>
            <p className="drop-sub">Text: .txt · .pdf · .md &nbsp;|&nbsp; Images: .jpg · .png · .gif · .webp</p>
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
                  {isImage(pending.name) && " · image → vision analysis → graph"}
                </span>
              </div>
            </div>
            <div className="pending-actions">
              <button className="upload-btn" onClick={uploadFile} disabled={uploading}>
                {uploading
                  ? isImage(pending.name) ? "Analyzing image…" : "Ingesting…"
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
                    {f.type === "image" && " · image → vision extracted"}
                  </span>
                  {f.imageDescription && (
                    <div className="image-description-box">
                      <span className="image-description-label">Vision extraction:</span>
                      <p className="image-description-text">{f.imageDescription}</p>
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
        Files are added to the active Cognee knowledge graph via{" "}
        <code style={{ fontFamily: "ui-monospace,monospace", fontSize: 12 }}>remember()</code>.
        Graph nodes and edges are extracted automatically. Query the new content immediately via
        Graph vs Vector or the Nexus panel.
      </div>
    </div>
  );
}
