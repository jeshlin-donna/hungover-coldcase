"""
main.py — FastAPI backend. Mirrors docs/API_CONTRACT.md exactly, so the frontend swaps
from the stdlib mock server to this with a one-line base-URL change.

Key design: it runs in TWO modes automatically.
  • LIVE      — cognee + LLM_API_KEY present → real recall/improve/forget via memory_service
  • DEGRADED  — deps/key missing → serves the curated mock JSON, never crashes
This is also our demo safety net (risk register: "live demo crashes"). The UI shows the
mode via GET /health so we always know which we're in.

Run (on a machine with deps):  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import base64
import functools
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend import case_store

IMAGE_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm"}
PDF_EXT = {".pdf"}
SPREADSHEET_EXTS = {".xlsx", ".xls", ".csv"}

def _file_modality(filename: str) -> str:
    """Return 'image' | 'audio' | 'video' | 'pdf' | 'spreadsheet' | 'text'"""
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS: return "image"
    if ext in AUDIO_EXTS: return "audio"
    if ext in VIDEO_EXTS: return "video"
    if ext in PDF_EXT: return "pdf"
    if ext in SPREADSHEET_EXTS: return "spreadsheet"
    return "text"

def _media_type_for(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".webp": "image/webp"}.get(ext)

_VISION_PROMPT = (
    "You are analyzing evidence for a cold case investigation. "
    "Image filename: {filename}\n\n"
    "Describe this image in forensic detail. Note: any visible people "
    "(physical description, clothing, distinguishing features), vehicles "
    "(make, model, color, license plates), locations or addresses, objects "
    "of interest, any visible text or timestamps, and anything potentially "
    "relevant to a criminal investigation. Be specific and factual."
)

# --- Provider detection ----------------------------------------------------------

def _using_groq() -> bool:
    """True when the configured LLM endpoint is Groq (api.groq.com)."""
    import os
    endpoint = os.getenv("LLM_ENDPOINT", "")
    return "groq.com" in endpoint


_groq_client = None

def _get_groq_client():
    """Lazily construct and cache a Groq SDK client."""
    global _groq_client
    if _groq_client is None:
        import os
        try:
            from groq import Groq
            _groq_client = Groq(api_key=os.getenv("LLM_API_KEY"))
        except ImportError:
            raise RuntimeError(
                "groq package not installed. Run: pip install groq"
            )
    return _groq_client


# --- Vision (image description) --------------------------------------------------

async def describe_image(content: bytes, filename: str, media_type: str) -> str:
    """Describe an image forensically. Routes to Groq or local Ollama based on .env.

    • Groq  (LLM_ENDPOINT contains groq.com): uses groq SDK vision model.
    • Ollama (default): calls /api/chat with base64 image — no SDK, no API key.

    Both run in asyncio.to_thread() so the event loop is never blocked.
    """
    import os
    b64 = base64.standard_b64encode(content).decode()
    prompt = _VISION_PROMPT.format(filename=filename)

    if _using_groq():
        vision_model = os.getenv("VISION_MODEL", "llava-v1.5-7b-4096-preview")
        client = _get_groq_client()

        def _call_groq():
            resp = client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }],
                max_tokens=1024,
            )
            return resp.choices[0].message.content

        return await asyncio.to_thread(_call_groq)

    else:
        # Local Ollama (default)
        import json
        import urllib.request
        vision_model = os.getenv("VISION_MODEL", "llava:7b")
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        payload = json.dumps({
            "model": vision_model,
            "messages": [{"role": "user", "content": prompt, "images": [b64]}],
            "stream": False,
        }).encode()

        def _call_ollama():
            req = urllib.request.Request(
                f"{ollama_base}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["message"]["content"]

        return await asyncio.to_thread(_call_ollama)


# --- Audio transcription ---------------------------------------------------------

_whisper_model = None


def _get_whisper_model():
    """Lazily load and cache the local Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("tiny")
    return _whisper_model


async def transcribe_audio(content: bytes, filename: str) -> str:
    """Transcribe audio. Routes to Groq Whisper API or local Whisper tiny model.

    • Groq: uses whisper-large-v3 via Groq SDK — fast, no local model download.
    • Ollama / local (default): uses openai-whisper tiny model locally.
    """
    import os
    suffix = Path(filename).suffix or ".mp3"

    if _using_groq():
        client = _get_groq_client()
        model = os.getenv("LLM_TRANSCRIPTION_MODEL", "whisper-large-v3")

        def _call_groq():
            return client.audio.transcriptions.create(
                model=model,
                file=(f"audio{suffix}", content),
            )

        resp = await asyncio.to_thread(_call_groq)
        return (resp.text or "").strip()

    # Local Whisper fallback
    import tempfile
    try:
        import whisper  # noqa: F401
    except ImportError:
        return "[Audio transcription unavailable: pip install openai-whisper]"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        def _transcribe():
            model = _get_whisper_model()
            result = model.transcribe(tmp_path)
            return result.get("text", "").strip()
        return await asyncio.to_thread(_transcribe)
    finally:
        os.unlink(tmp_path)


async def extract_video_description(content: bytes, filename: str) -> str:
    """Extract keyframes from video and describe each with Claude vision."""
    import tempfile, os
    try:
        import cv2
    except ImportError:
        return "[Video analysis unavailable: pip install opencv-python-headless]"
    suffix = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        def _extract_frames():
            # OpenCV's VideoCapture/read/imencode calls are blocking; do the frame
            # grabbing in a worker thread and only return small JPEG buffers, so
            # the event loop isn't blocked while frames are decoded.
            cap = cv2.VideoCapture(tmp_path)
            try:
                fps = cap.get(cv2.CAP_PROP_FPS) or 1
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                # 1 frame every 10 seconds, max 5 frames
                interval = max(1, int(fps * 10))
                frame_indices = list(range(0, total, interval))[:5]
                frames = []
                for idx in frame_indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    _, buf = cv2.imencode(".jpg", frame)
                    frames.append((idx / fps, buf.tobytes()))
                return frames
            finally:
                cap.release()

        frames = await asyncio.to_thread(_extract_frames)
        descriptions = []
        for ts, jpeg_bytes in frames:
            desc = await describe_image(jpeg_bytes, f"frame_{ts:.1f}s.jpg", "image/jpeg")
            descriptions.append(f"[{ts:.1f}s into video] {desc}")
        return "\n\n".join(descriptions) if descriptions else "[No frames extracted]"
    finally:
        os.unlink(tmp_path)


async def extract_pdf_content(content: bytes, filename: str) -> str:
    """Extract text from PDF; fall back to Claude vision for scanned pages."""
    try:
        import fitz  # pymupdf
    except ImportError:
        return "[PDF extraction unavailable: pip install pymupdf]"

    def _extract_pages():
        # PyMuPDF text/pixmap extraction is CPU-bound and blocking; do it in a
        # worker thread. Scanned pages come back as JPEG bytes for async vision
        # description instead of being described inline (which would block here).
        doc = fitz.open(stream=content, filetype="pdf")
        pages = []
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append(("text", page_num, text))
            else:
                pix = page.get_pixmap(dpi=150)
                pages.append(("image", page_num, pix.tobytes("jpeg")))
        return pages

    pages = await asyncio.to_thread(_extract_pages)
    texts = []
    for kind, page_num, payload in pages:
        if kind == "text":
            texts.append(f"[Page {page_num + 1}]\n{payload}")
        else:
            desc = await describe_image(payload, f"{filename}_page{page_num + 1}.jpg", "image/jpeg")
            texts.append(f"[Page {page_num + 1} — scanned image]\n{desc}")
    return "\n\n".join(texts)


def parse_spreadsheet(content: bytes, filename: str) -> str:
    """Parse Excel/CSV into a structured text description for Cognee ingestion."""
    try:
        import pandas as pd
        import io
    except ImportError:
        return "[Spreadsheet parsing unavailable: pip install pandas openpyxl]"
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
        rows_text = df.to_string(index=False, max_rows=500)
        return (
            f"SPREADSHEET EVIDENCE — {filename}\n"
            f"Columns: {', '.join(str(c) for c in df.columns)}\n"
            f"Rows: {len(df)}\n\n"
            f"{rows_text}"
        )
    except Exception as e:
        return f"[Spreadsheet parse error: {e}]"


ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "frontend" / "mock"
BENCH = ROOT / "benchmark" / "results.json"
HERO = ROOT / "data" / "hero_case"
DATASET = "coldcases"
UPLOADED_NODES: list[dict] = []
PENDING_INGESTIONS: dict[str, dict] = {}

# --- try to go LIVE; fall back to DEGRADED cleanly ---------------------------
LIVE = False
mem = None
try:
    import os
    import sys
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    sys.path.insert(0, str(ROOT / "backend"))
    if os.getenv("LLM_API_KEY"):
        import memory_service as mem  # noqa
        LIVE = True
except Exception as e:  # pragma: no cover
    print(f"[backend] DEGRADED mode ({type(e).__name__}: {e}) — serving mock data")

app = FastAPI(title="ColdCache — Cold Case Connector")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


@functools.lru_cache(maxsize=32)
def _read_mock_file(name: str) -> str:
    # Cache the raw file text (not the parsed dict!) so repeated /graph, /timeline,
    # etc. calls skip disk I/O, while mock() below still hands each caller a fresh
    # dict — some callers (e.g. /graph) mutate the returned object in place.
    return (MOCK / name).read_text()


def mock(name: str) -> dict:
    return json.loads(_read_mock_file(name))


@functools.lru_cache(maxsize=1)
def known_doc_ids() -> list[str]:
    # The hero-case corpus is static demo data bundled with the repo, so the
    # DOC_ID glob+regex scan only needs to run once per process instead of on
    # every /recall, /recall/compare, and /chat call.
    ids = []
    for p in HERO.glob("*.md"):
        m = re.search(r"DOC_ID:\s*([A-Z0-9\-]+)", p.read_text())
        if m:
            ids.append(m.group(1))
    return sorted(ids, key=len, reverse=True)


def extract_ids(text: str, ids: list[str]) -> list[str]:
    pos = [(text.find(i), i) for i in ids if text.find(i) >= 0]
    return [i for _, i in sorted(pos)]


# Fixed multi-hop probe used to measure a real recall@3 delta around improve()
# in /resolve (mirrors benchmark/benchmark_improve.py's q17 alibi-vs-evidence query,
# so the number quoted in the demo is measured the same way as the benchmark).
RESOLVE_PROBE_QUERY = (
    "Does Daniel Marsh's alibi for the night of the Riverside burglary hold up "
    "against the other evidence?"
)
RESOLVE_PROBE_GOLD = ["MARSH-ALIBI", "MARSH-RECEIPT"]


def _recall_at_3(ranked: list[str], gold: list[str]) -> float:
    if not gold:
        return 0.0
    return len(set(ranked[:3]) & set(gold)) / len(set(gold))


# --- request models ----------------------------------------------------------
class RecallReq(BaseModel):
    query: str
    mode: str = "graph"  # graph | vector | insights

class HunchReq(BaseModel):
    text: str
    session_id: str = "case-001"

class ResolveReq(BaseModel):
    session_ids: list[str] = ["case-001"]

class ExpungeReq(BaseModel):
    dataset: str = "case:RV-0788"

class NexusReq(BaseModel):
    from_node: str = "suspect:daniel-marsh"
    to_node: str = "case:RV-0788"

class InterrogationReq(BaseModel):
    suspect_id: str = "suspect:daniel-marsh"
    focus_case: str = "case:RV-0788"

class WhatIfReq(BaseModel):
    hypothesis: str
    inject_edge: dict = {}

class ChatReq(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user"|"assistant", "text": "..."}]

class ConfirmIngestReq(BaseModel):
    review_id: str
    extracted_text: str | None = None
    context: str | None = None

class BatchConfirmIngestReq(BaseModel):
    items: list[ConfirmIngestReq]

class CaseCreateReq(BaseModel):
    title: str
    reference_number: str | None = None
    description: str | None = None
    jurisdiction: str | None = None
    incident_date: str | None = None

class CaseUpdateReq(BaseModel):
    title: str | None = None
    reference_number: str | None = None
    description: str | None = None
    jurisdiction: str | None = None
    incident_date: str | None = None
    status: str | None = None

class EvidenceConfirmReq(BaseModel):
    reviewed_text: str
    context: str = ""


_worker_task = None


async def _durable_job_worker():
    """Single durable worker; queued/running state survives browser and process restarts."""
    while True:
        job = await asyncio.to_thread(case_store.claim_job)
        if not job:
            await asyncio.sleep(0.75)
            continue
        try:
            item = await asyncio.to_thread(case_store.get_evidence, job["evidence_id"])
            case = await asyncio.to_thread(case_store.get_case, job["case_id"])
            if not item or not case:
                raise RuntimeError("Case or evidence record no longer exists")
            if job["kind"] == "analyze":
                await asyncio.to_thread(case_store.job_progress, job["id"], "reading_file", 10)
                content = await asyncio.to_thread(case_store.storage_path(item).read_bytes)
                await asyncio.to_thread(case_store.job_progress, job["id"], f"analyzing_{item['modality']}", 25)
                output, _ = await _extract_upload(content, item["original_filename"])
                if await asyncio.to_thread(case_store.is_cancel_requested, job["id"]):
                    await asyncio.to_thread(case_store.finish_cancelled, job)
                    continue
                if item["context"]:
                    output = (f"USER-PROVIDED SUBMISSION CONTEXT\n{item['context']}\n\n"
                              f"MODEL-GENERATED / EXTRACTED CONTENT — REVIEW BEFORE INGESTION\n{output}")
                await asyncio.to_thread(case_store.job_progress, job["id"], "saving_review", 92)
                await asyncio.to_thread(case_store.finish_analysis, job, output)
            elif job["kind"] == "ingest":
                await asyncio.to_thread(case_store.job_progress, job["id"], "staging_cognee", 25)
                if LIVE:
                    await mem.remember(item["reviewed_text"], dataset=case["dataset_name"])
                if await asyncio.to_thread(case_store.is_cancel_requested, job["id"]):
                    await asyncio.to_thread(case_store.finish_cancelled, job)
                    continue
                await asyncio.to_thread(case_store.job_progress, job["id"], "indexing_graph", 94)
                await asyncio.to_thread(case_store.finish_ingestion, job)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await asyncio.to_thread(case_store.fail_job, job, str(e))


@app.on_event("startup")
async def start_durable_worker():
    global _worker_task
    await asyncio.to_thread(case_store.init_db)
    _worker_task = asyncio.create_task(_durable_job_worker())


@app.on_event("shutdown")
async def stop_durable_worker():
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass


# --- routes (match API_CONTRACT.md) ------------------------------------------
@app.post("/cases", status_code=201)
async def create_case(req: CaseCreateReq):
    from fastapi import HTTPException
    if not req.title.strip():
        raise HTTPException(422, "Case title is required.")
    return await asyncio.to_thread(case_store.create_case, req.model_dump())


@app.get("/cases")
async def cases_list():
    return {"cases": await asyncio.to_thread(case_store.list_cases)}


@app.get("/cases/{case_id}")
async def case_detail(case_id: str):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.get_case, case_id)
    if not case: raise HTTPException(404, "Case not found.")
    case["evidence"] = await asyncio.to_thread(case_store.list_evidence, case_id)
    case["jobs"] = await asyncio.to_thread(case_store.list_jobs, case_id)
    return case


@app.patch("/cases/{case_id}")
async def case_update(case_id: str, req: CaseUpdateReq):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.update_case, case_id, req.model_dump(exclude_none=True))
    if not case: raise HTTPException(404, "Case not found.")
    return case


@app.post("/cases/{case_id}/evidence", status_code=202)
async def case_upload_evidence(
    case_id: str, files: list[UploadFile] = File(...), contexts: str = Form("[]")
):
    from fastapi import HTTPException
    if not await asyncio.to_thread(case_store.get_case, case_id):
        raise HTTPException(404, "Case not found.")
    try: parsed = json.loads(contexts)
    except json.JSONDecodeError: raise HTTPException(422, "contexts must be a JSON array.")
    if not isinstance(parsed, list): raise HTTPException(422, "contexts must be a JSON array.")
    parsed += [""] * (len(files) - len(parsed))
    results = []
    for index, upload in enumerate(files):
        content = await upload.read()
        item, job = await asyncio.to_thread(
            case_store.save_evidence, case_id, upload.filename or f"file-{index+1}", content,
            upload.content_type, _file_modality(upload.filename or ""), str(parsed[index] or "")
        )
        results.append({"evidence": item, "job": job})
    return {"ok": True, "results": results}


@app.get("/cases/{case_id}/evidence")
async def case_evidence_list(case_id: str):
    from fastapi import HTTPException
    if not await asyncio.to_thread(case_store.get_case, case_id): raise HTTPException(404, "Case not found.")
    return {"evidence": await asyncio.to_thread(case_store.list_evidence, case_id),
            "jobs": await asyncio.to_thread(case_store.list_jobs, case_id)}


@app.post("/cases/{case_id}/evidence/{evidence_id}/confirm", status_code=202)
async def case_confirm_evidence(case_id: str, evidence_id: str, req: EvidenceConfirmReq):
    from fastapi import HTTPException
    if not req.reviewed_text.strip(): raise HTTPException(422, "Reviewed evidence cannot be empty.")
    try:
        job = await asyncio.to_thread(case_store.queue_ingestion, case_id, evidence_id,
                                      req.reviewed_text.strip(), req.context.strip())
    except KeyError: raise HTTPException(404, "Evidence not found in this case.")
    return {"ok": True, "job": job}


@app.post("/cases/{case_id}/evidence/{evidence_id}/retry", status_code=202)
async def case_retry_evidence(case_id: str, evidence_id: str):
    from fastapi import HTTPException
    item = await asyncio.to_thread(case_store.get_evidence, evidence_id)
    if not item or item["case_id"] != case_id: raise HTTPException(404, "Evidence not found.")
    kind = "ingest" if item["status"] == "ingestion_failed" else "analyze"
    try: job = await asyncio.to_thread(case_store.retry_evidence, case_id, evidence_id, kind)
    except KeyError: raise HTTPException(404, "Evidence not found.")
    return {"ok": True, "job": job}


@app.post("/cases/{case_id}/evidence/{evidence_id}/cancel")
async def case_cancel_evidence(case_id: str, evidence_id: str):
    await asyncio.to_thread(case_store.cancel_job, case_id, evidence_id)
    return {"ok": True}


@app.get("/cases/{case_id}/jobs")
async def case_jobs(case_id: str):
    return {"jobs": await asyncio.to_thread(case_store.list_jobs, case_id)}


@app.get("/cases/{case_id}/stats")
async def case_stats(case_id: str):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.get_case, case_id)
    if not case: raise HTTPException(404, "Case not found.")
    evidence = await asyncio.to_thread(case_store.list_evidence, case_id)
    jobs = await asyncio.to_thread(case_store.list_jobs, case_id)
    return {"nodes": sum(1 for item in evidence if item["status"] == "ingested"),
            "docs": sum(1 for item in evidence if item["status"] == "ingested"),
            "jurisdictions": 1 if case.get("jurisdiction") else 0,
            "active_jobs": sum(1 for job in jobs if job["status"] in ("queued", "running")),
            "graph_revision": case["graph_revision"], "mode": "live" if LIVE else "degraded"}


@app.get("/cases/{case_id}/graph")
async def case_graph(case_id: str):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.get_case, case_id)
    if not case: raise HTTPException(404, "Case not found.")
    evidence = await asyncio.to_thread(case_store.list_evidence, case_id)
    nodes = [{"id": f"evidence:{item['id']}", "label": item["original_filename"],
              "type": "evidence", "modality": item["modality"]}
             for item in evidence if item["status"] == "ingested"]
    return {"nodes": nodes, "edges": [], "contradictions": [],
            "graph_revision": case["graph_revision"], "mode": "live" if LIVE else "degraded"}


@app.post("/cases/{case_id}/chat")
async def case_chat(case_id: str, req: ChatReq):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.get_case, case_id)
    if not case: raise HTTPException(404, "Case not found.")
    if not LIVE:
        return {"answer": "The case knowledge service is in degraded mode. Your evidence remains saved, but an LLM is required for answers.", "sources": [], "mode": "degraded"}
    history = "\n".join(f"{x.get('role','user')}: {x.get('text','')}" for x in req.history[-8:])
    query = f"Conversation context (not evidence):\n{history}\n\nLatest question: {req.message}" if history else req.message
    res = await mem.recall(query, mode=mem.RecallMode.GRAPH, dataset=case["dataset_name"])
    return {"answer": res.answer, "sources": [], "mode": "live"}


@app.get("/cases/{case_id}/chat/suggestions")
async def case_chat_suggestions(case_id: str):
    from fastapi import HTTPException
    case = await asyncio.to_thread(case_store.get_case, case_id)
    if not case: raise HTTPException(404, "Case not found.")
    fallback = ["What facts are established in this case?", "Which evidence needs corroboration?", "What should be investigated next?"]
    if not LIVE or case["graph_revision"] == 0: return {"suggestions": fallback, "mode": "degraded"}
    try:
        res = await mem.recall("Return exactly three concise investigative questions, one per line.", mode=mem.RecallMode.GRAPH, dataset=case["dataset_name"])
        lines = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip() for line in res.answer.splitlines()]
        return {"suggestions": [line for line in lines if line.endswith("?")][:3] or fallback, "mode": "live"}
    except Exception as e: return {"suggestions": fallback, "mode": "degraded", "error": str(e)}


@app.get("/health")
def health():
    return {"ok": True, "mode": "live" if LIVE else "degraded"}


@app.get("/stats")
def stats():
    # Stats must stay cheap: do not invoke graph recall just to paint the header.
    graph_payload = mock("graph.json")
    graph_payload["nodes"].extend(UPLOADED_NODES)
    nodes = graph_payload.get("nodes", [])
    jurisdictions = {n["id"] for n in nodes if n.get("type") == "jurisdiction"}
    return {
        "nodes": len(nodes),
        "docs": len(known_doc_ids()) + len(UPLOADED_NODES),
        "jurisdictions": len(jurisdictions),
        "alibi_break": bool(graph_payload.get("contradictions")),
        "mode": "live" if LIVE else "degraded",
    }


@app.get("/graph")
async def graph():
    # The curated graph stays the base response (risk register: "Live demo crashes" ->
    # degraded mode must never fail) — it's faithful to the hero case and the reliable
    # demo visual. In LIVE mode we additionally attach a real Cognee TRIPLET_COMPLETION
    # ("insights") narrative over the same case data on top of it, so /graph actually
    # exercises the 3rd recall mode instead of only ever serving static curation.
    payload = mock("graph.json")
    payload["nodes"].extend(UPLOADED_NODES)
    payload["mode"] = "degraded"
    if LIVE:
        try:
            res = await mem.recall(
                "Describe the key relationships connecting the suspect, tool, vehicle, "
                "MO, and cases in this investigation",
                mode=mem.RecallMode.INSIGHTS,
                dataset=DATASET,
            )
            payload["cognee_insight"] = res.answer
            payload["mode"] = "live"
        except Exception as e:
            payload["cognee_insight_error"] = str(e)
    return payload


@app.get("/graph/temporal")
async def graph_temporal(time: str = None):
    """Time-windowed graph view for the Evidence Board's temporal slider.

    Returns only nodes dated at or before `time` (nodes without a `date`
    field, e.g. jurisdictions, are treated as always-visible context anchors)
    plus edges whose endpoints are both currently visible.
    """
    full = await graph()
    if not time:
        return full
    nodes = full.get("nodes", [])
    visible_ids = {
        n["id"] for n in nodes if not n.get("date") or n["date"] <= time
    }
    filtered_nodes = [n for n in nodes if n["id"] in visible_ids]
    filtered_edges = [
        e for e in full.get("edges", [])
        if e["source"] in visible_ids and e["target"] in visible_ids
    ]
    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "contradictions": full.get("contradictions", []),
        "time": time,
        "mode": full.get("mode", "degraded"),
    }


@app.get("/timeline")
def timeline():
    return mock("timeline.json")


@app.get("/contradictions")
async def contradictions():
    if not LIVE:
        return {"contradictions": mock("graph.json").get("contradictions", [])}
    # Use TRIPLET_COMPLETION to find conflicting triples
    try:
        res = await mem.recall(
            "Find contradictions: alibi claim vs physical location evidence for Daniel Marsh",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        # Also check the motel vs alibi specifically
        alibi_res = await mem.recall(
            "Where was Daniel Marsh on the night of the Riverside View burglary according to his alibi statement vs motel records?",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        curated = mock("graph.json").get("contradictions", [])
        # Attach the live cognee insight to the curated contradiction
        if curated:
            curated[0]["cognee_insight"] = alibi_res.answer
        return {"contradictions": curated, "mode": "live", "search_type": "GRAPH_COMPLETION"}
    except Exception as e:
        return {"contradictions": mock("graph.json").get("contradictions", []), "mode": "degraded", "error": str(e)}


@app.get("/benchmark")
def benchmark():
    return json.loads(BENCH.read_text()) if BENCH.exists() else {
        "note": "run benchmark/benchmark.py to populate results.json"}


@app.get("/recall/compare")
async def recall_compare(query: str = "", dataset: str = "all"):
    if not LIVE:
        return mock("recall_compare.json")
    ids = known_doc_ids()
    # dataset param: "hero" uses DATASET; "all" also uses DATASET (simplification for now)
    target_dataset = DATASET if dataset == "hero" else DATASET
    out = {"query": query, "dataset": dataset, "results": {}}
    for label, mode in (("naive_vector", None), ("cognee_vector", mem.RecallMode.VECTOR),
                        ("cognee_graph", mem.RecallMode.GRAPH)):
        if mode is None:
            # naive baseline handled in benchmark; here we only expose Cognee modes live.
            continue
        res = await mem.recall(query, mode=mode, dataset=target_dataset)
        srcs = extract_ids(str(res.raw), ids)
        out["results"][label] = {"answer": res.answer, "sources": srcs[:5],
                                 "connects": sorted({s.split('-')[0] + '-' + s.split('-')[1]
                                                     for s in srcs if '-' in s})}
    return out


@app.post("/recall")
async def recall(req: RecallReq):
    if not LIVE:
        cmp = mock("recall_compare.json")["results"]
        key = {"graph": "cognee_graph", "vector": "cognee_vector"}.get(req.mode, "cognee_graph")
        return {"mode": req.mode, **cmp[key]}
    mode = {"graph": mem.RecallMode.GRAPH, "vector": mem.RecallMode.VECTOR,
            "insights": mem.RecallMode.INSIGHTS}.get(req.mode, mem.RecallMode.GRAPH)
    res = await mem.recall(req.query, mode=mode, dataset=DATASET)
    return {"mode": req.mode, "answer": res.answer,
            "sources": extract_ids(str(res.raw), known_doc_ids())[:5]}


@app.post("/hunch")
async def hunch(req: HunchReq):
    if LIVE:
        await mem.log_hunch(req.text, session_id=req.session_id, dataset=DATASET)
    return {"ok": True, "session_id": req.session_id}


@app.post("/resolve")
async def resolve(req: ResolveReq):
    if not LIVE:
        return {"ok": True, "metric": "recall@3 on multi-hop", "before": 0.42, "after": 0.71,
                "mode": "degraded"}

    ids = known_doc_ids()

    # Best-effort instrumentation around the real improve() call — measurement
    # failures must never block resolve_case() itself from running.
    before_score = None
    try:
        before_res = await mem.recall(RESOLVE_PROBE_QUERY, mode=mem.RecallMode.GRAPH, dataset=DATASET)
        before_score = _recall_at_3(extract_ids(str(before_res.raw), ids), RESOLVE_PROBE_GOLD)
    except Exception as e:
        print(f"[resolve] before-probe failed: {type(e).__name__}: {e}")

    await mem.resolve_case(session_ids=req.session_ids, dataset=DATASET)

    after_score = None
    try:
        after_res = await mem.recall(RESOLVE_PROBE_QUERY, mode=mem.RecallMode.GRAPH, dataset=DATASET)
        after_score = _recall_at_3(extract_ids(str(after_res.raw), ids), RESOLVE_PROBE_GOLD)
    except Exception as e:
        print(f"[resolve] after-probe failed: {type(e).__name__}: {e}")

    if before_score is None or after_score is None:
        # Real improve() ran; only the probe measurement is degraded, so say so
        # rather than silently returning the same static numbers as full-mock mode.
        return {"ok": True, "metric": "recall@3 on multi-hop", "before": 0.42, "after": 0.71,
                "mode": "improve-ok-metric-degraded"}

    return {
        "ok": True,
        "metric": "recall@3 on multi-hop (probe: alibi vs evidence)",
        "before": round(before_score, 3),
        "after": round(after_score, 3),
        "mode": "live",
    }


@app.post("/expunge")
async def expunge(req: ExpungeReq):
    if LIVE:
        await mem.expunge(dataset=DATASET)
    g = mock("graph.json")
    tag = req.dataset.split(":")[-1]
    removed = [n["id"] for n in g["nodes"] if tag in n["id"]]
    g["nodes"] = [n for n in g["nodes"] if n["id"] not in removed]
    g["edges"] = [e for e in g["edges"]
                  if e["source"] not in removed and e["target"] not in removed]
    return {"ok": True, "removed": removed, "graph": g}


# --- new endpoints -----------------------------------------------------------

@app.get("/missing-hours")
async def missing_hours():
    payload = {
        "suspect": "Daniel R. Marsh",
        "gaps": [
            {
                "id": "gap-001",
                "start": "2023-03-03T01:30:00",
                "end": "2023-03-03T04:00:00",
                "duration_hours": 2.5,
                "label": "Night of MH-2023-0312 burglary",
                "urgency": "high",
                "recommendation": "Pull CCTV from Maple Heights Commercial District (cameras on Oak & 3rd). Request cell tower data for Clearwater County towers.",
                "nearby_events": ["MH-2023-0312 occurred 02:15", "Witness saw dark sedan 02:30"]
            },
            {
                "id": "gap-002",
                "start": "2023-11-18T22:00:00",
                "end": "2023-11-19T06:00:00",
                "duration_hours": 8.0,
                "label": "Night of RV-2023-0788 — alibi contradicted",
                "urgency": "critical",
                "recommendation": "Alibi already broken by card records. Request full cell tower log for Hale County 2023-11-18 22:00 – 2023-11-19 06:00. Subpoena motel check-in video.",
                "nearby_events": [
                    "Card record: fuel purchase 23:31 (6.1mi from scene)",
                    "Card record: motel check-in 00:48 (4.2mi from scene)",
                    "RV-2023-0788 occurred ~02:00"
                ]
            },
            {
                "id": "gap-003",
                "start": "2025-02-03T23:00:00",
                "end": "2025-02-04T04:00:00",
                "duration_hours": 5.0,
                "label": "Night of MH-2025-0102 — no alibi provided",
                "urgency": "high",
                "recommendation": "No alibi offered for this night. Pull residential camera data from Maple Heights Court area. Request phone records.",
                "nearby_events": ["MH-2025-0102 occurred ~01:15", "Neighbor reported noise ~01:20"]
            }
        ],
        "total_gaps": 3,
        "critical_gaps": 1,
        "note": "Information bounty: closing gap-002 with cell tower data would establish physical presence at scene."
    }
    if LIVE:
        res = await mem.recall(
            "What are the known gaps in Daniel Marsh's timeline and alibi?",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        payload["cognee_insight"] = res.answer
    return payload


@app.post("/nexus")
async def nexus(req: NexusReq):
    # Static mock paths keyed by (from_node, to_node)
    mock_paths: dict[tuple[str, str], dict] = {
        ("suspect:daniel-marsh", "case:RV-0788"): {
            "from": "suspect:daniel-marsh",
            "to": "case:RV-0788",
            "path": [
                {"node": "suspect:daniel-marsh", "label": "Daniel R. Marsh"},
                {"edge": "possessed", "weight": "verified"},
                {"node": "tool:pry-8mm", "label": "Pry bar · 8mm · left-edge nick"},
                {"edge": "tool_used", "weight": "forensic"},
                {"node": "case:RV-0788", "label": "RV-2023-0788"}
            ],
            "hops": 2,
            "strength": "strong",
            "narrative": "Marsh possessed the pry bar (verified — recovered from his garage) → same tool forensically matched to the Riverside scene."
        },
        ("jur:maple-heights", "jur:riverside"): {
            "from": "jur:maple-heights",
            "to": "jur:riverside",
            "path": [
                {"node": "jur:maple-heights", "label": "Maple Heights Jurisdiction"},
                {"edge": "tool_used", "weight": "forensic"},
                {"node": "tool:pry-8mm", "label": "Pry bar · 8mm · left-edge nick"},
                {"edge": "tool_used", "weight": "forensic"},
                {"node": "jur:riverside", "label": "Riverside Jurisdiction"}
            ],
            "hops": 2,
            "strength": "strong",
            "narrative": "The same pry bar (8mm nick) links crimes across both jurisdictions — the cross-jurisdiction thread."
        },
        ("alibi:marsh-nov19", "case:RV-0788"): {
            "from": "alibi:marsh-nov19",
            "to": "case:RV-0788",
            "path": [
                {"node": "alibi:marsh-nov19", "label": "Marsh alibi — night of Nov 18-19"},
                {"edge": "contradicted_by", "weight": "verified"},
                {"node": "receipt:marsh-nov19", "label": "Card records: fuel + motel near scene"},
                {"edge": "places_suspect_at", "weight": "forensic"},
                {"node": "case:RV-0788", "label": "RV-2023-0788"}
            ],
            "hops": 2,
            "strength": "strong",
            "narrative": "The alibi (Marsh claims he was 300 miles away) is directly contradicted by card records that place him within 4-6 miles of the Riverside scene that night."
        }
    }

    key = (req.from_node, req.to_node)
    result = mock_paths.get(key, {
        "from": req.from_node,
        "to": req.to_node,
        "path": [],
        "hops": 0,
        "strength": "unknown",
        "narrative": f"No known path from {req.from_node} to {req.to_node} in the current graph."
    })

    if LIVE:
        res = await mem.recall(
            f"What connects {req.from_node} to {req.to_node}?",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        result["cognee_insight"] = res.answer

    return result


@app.post("/interrogation")
async def interrogation(req: InterrogationReq):
    payload = {
        "suspect": "Daniel R. Marsh",
        "focus_case": "RV-2023-0788",
        "strategy": "Lead with the card records. He doesn't know we have the motel receipt. The alibi collapses on the second question.",
        "questions": [
            {
                "id": "q1",
                "question": "Mr. Marsh, where were you on the night of November 18th into the 19th, 2023?",
                "type": "open",
                "expected_lie": "Claims to be 300 miles away in Pineford",
                "trap": None,
                "evidence_held_back": "Card records, motel receipt"
            },
            {
                "id": "q2",
                "question": "Can you explain this card transaction — a fuel purchase in Hale County at 11:31 PM on November 18th?",
                "type": "confrontation",
                "expected_lie": "Denial or 'someone else used my card'",
                "trap": "Follow up: 'And the motel check-in at 12:48 AM, 4.2 miles from 902 Riverside Lane?'",
                "evidence_held_back": None
            },
            {
                "id": "q3",
                "question": "Tell me about the tools you keep in your garage — specifically any pry bars.",
                "type": "fishing",
                "expected_lie": "Claims no pry bars / doesn't know what we found",
                "trap": "We have the tool recovered. Ask him to explain why its blade matches all three scenes.",
                "evidence_held_back": "Tool match forensics"
            },
            {
                "id": "q4",
                "question": "Do you know anyone who drives a dark blue Honda Accord, partial plate 8K?",
                "type": "fishing",
                "expected_lie": "Denial",
                "trap": "DMV records show he registered a 2016 Honda Accord in that color range.",
                "evidence_held_back": "Vehicle registration"
            }
        ],
        "weak_edges": [
            "alibi:marsh-nov19 (unverified — contradicted by card records)",
            "vehicle ownership (not yet confirmed in record)"
        ],
        "cognee_insight": None
    }

    if LIVE:
        res = await mem.recall(
            f"What are the weakest claims and best interrogation angles for Daniel Marsh regarding {req.focus_case}?",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        payload["cognee_insight"] = res.answer

    return payload


@app.post("/whatif")
async def whatif(req: WhatIfReq):
    payload = {
        "hypothesis": req.hypothesis,
        "injected_edge": req.inject_edge,
        "impact": "moderate",
        "recalculated_scores": {
            "suspect:daniel-marsh": {
                "before": 0.87,
                "after": 0.79,
                "delta": -0.08,
                "reason": "Vehicle witness testimony weakened; forensic tool match still holds"
            },
            "vehicle:blue-sedan": {
                "before": 0.91,
                "after": 0.61,
                "delta": -0.30,
                "reason": "If C is lying, sedan sighting confidence drops"
            }
        },
        "narrative": "Even without Witness C's testimony, the forensic tool match (8mm nick) and card records place Marsh at the scene. The vehicle sighting becomes circumstantial but the physical evidence chain is intact.",
        "recommended_next": "Verify vehicle registration independently — don't rely on Witness C's description.",
        "cognee_insight": None
    }

    if LIVE:
        res = await mem.recall(
            req.hypothesis,
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET
        )
        payload["cognee_insight"] = res.answer

    return payload


@app.post("/chat")
async def chat(req: ChatReq):
    if not LIVE:
        return {
            "answer": "Based on the case graph, Daniel Marsh was identified across three burglary incidents in two jurisdictions. The tool-mark evidence (8mm left-nick pry blade) and the dark blue Honda Accord connect all three scenes. The motel receipt places him 4.2 miles from the Riverside View scene at 00:48.",
            "sources": ["MH-0102-FOR", "RV-0788-WIT", "MARSH-ALIBI"],
            "mode": "degraded"
        }
    recent = req.history[-8:]
    history = "\n".join(
        f"{item.get('role', 'user')}: {item.get('text', '')}" for item in recent
    )
    query = req.message
    if history:
        query = (
            "Answer the investigator's latest question using the case knowledge graph. "
            "Use the conversation only to resolve references; do not treat it as evidence.\n\n"
            f"Conversation:\n{history}\n\nLatest question: {req.message}"
        )
    res = await mem.recall(query, mode=mem.RecallMode.GRAPH, dataset=DATASET)
    sources = extract_ids(str(res.raw), known_doc_ids())[:5]
    return {"answer": res.answer, "sources": sources, "mode": "live"}


@app.get("/chat/suggestions")
async def chat_suggestions():
    fallback = [
        "What evidence connects incidents across jurisdictions?",
        "Which claims are contradicted by verified records?",
        "What important gap should an investigator pursue next?",
    ]
    if not LIVE:
        return {"suggestions": fallback, "mode": "degraded"}
    try:
        res = await mem.recall(
            "Based only on this case graph, propose exactly three concise, useful questions "
            "an investigator should ask next. Return one question per line, no numbering.",
            mode=mem.RecallMode.GRAPH,
            dataset=DATASET,
        )
        suggestions = []
        for line in res.answer.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if cleaned and cleaned.endswith("?"):
                suggestions.append(cleaned)
        return {"suggestions": suggestions[:3] or fallback, "mode": "live"}
    except Exception as e:
        return {"suggestions": fallback, "mode": "degraded", "error": str(e)}


@app.get("/report")
async def report():
    if not LIVE:
        return {
            "title": "Case Summary — Daniel Marsh Serial Burglary Series",
            "generated_at": "2025-02-10",
            "sections": [
                {"heading": "Suspect", "content": "Daniel Marsh, DOB 1987-04-12. Identified across three residential burglaries spanning two jurisdictions (Millbrook Heights PD and Riverside View PD)."},
                {"heading": "MO", "content": "Entry via 8mm left-nick pry blade on basement windows. Targets electronics and jewelry. Getaway vehicle: dark blue 2015-2018 Honda Accord, partial plate 7XK."},
                {"heading": "Alibi Contradiction", "content": "Marsh claimed to be 300 miles out of state on 2025-02-04. Motel receipt (Grand Stay Inn, 4.2 miles from scene) places him locally at 00:48."},
                {"heading": "Cross-Jurisdiction Link", "content": "Tool-mark forensics from MH-0102 and RV-0788 confirmed by same examiner. Same blade profile, same entry method. Connected via Cognee graph traversal — not surfaced by either department's individual search."},
                {"heading": "Recommendation", "content": "File joint warrant. Prioritize vehicle search for dark blue Accord. Subpoena Grand Stay Inn records for full stay history."}
            ],
            "mode": "degraded"
        }
    sections = []
    for heading, q in [
        ("Suspect", "Who is the primary suspect and what is their background?"),
        ("MO", "What is the suspect's modus operandi across all cases?"),
        ("Alibi Contradiction", "What contradicts the suspect's alibi?"),
        ("Cross-Jurisdiction Link", "How are the Millbrook Heights and Riverside View cases connected?"),
        ("Recommendation", "What are the recommended next investigative steps?"),
    ]:
        res = await mem.recall(q, mode=mem.RecallMode.GRAPH, dataset=DATASET)
        sections.append({"heading": heading, "content": res.answer})
    return {"title": "Case Summary — Daniel Marsh Serial Burglary Series",
            "sections": sections, "mode": "live"}


@app.get("/suspect-timeline")
async def suspect_timeline(suspect: str = "daniel-marsh"):
    if not LIVE:
        return {"suspect": suspect, "events": [
            {"date": "2023-03-03", "time": "02:15", "location": "Millbrook Heights", "event": "Burglary at 412 Oakwood Drive — 8mm pry blade entry, electronics taken", "confidence": 0.95, "sources": ["MH-0102-NARR", "MH-0102-FOR"]},
            {"date": "2023-03-03", "time": "03:40", "location": "I-94 corridor", "event": "Dark blue Accord seen on traffic camera heading south", "confidence": 0.72, "sources": ["MH-0102-NARR"]},
            {"date": "2023-11-19", "time": "01:30", "location": "Millbrook Heights", "event": "Second burglary — same MO, same tool marks", "confidence": 0.97, "sources": ["MH-0312-FOR", "MH-0312-NARR"]},
            {"date": "2025-02-04", "time": "00:48", "location": "Grand Stay Inn (4.2mi from scene)", "event": "Motel check-in — contradicts alibi claim of being 300mi away", "confidence": 0.99, "sources": ["MARSH-RECEIPT", "MARSH-ALIBI"]},
            {"date": "2025-02-04", "time": "02:30", "location": "Riverside View", "event": "Burglary at 788 Riverside — third incident, arrested 6 days later", "confidence": 0.99, "sources": ["RV-0788-NARR", "RV-0788-FOR"]},
            {"date": "2025-02-10", "time": "14:00", "location": "Riverside View PD", "event": "Arrest — doorbell camera identified vehicle", "confidence": 1.0, "sources": ["MH-0102-ARR"]}
        ], "mode": "degraded"}
    res = await mem.recall(
        f"Reconstruct a chronological timeline of all movements and events involving {suspect} across all cases",
        mode=mem.RecallMode.GRAPH, dataset=DATASET
    )
    return {"suspect": suspect, "cognee_narrative": res.answer, "mode": "live"}


@app.post("/transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    content = await file.read()
    fname = file.filename or "recording.webm"
    if LIVE:
        try:
            text = await transcribe_audio(content, fname)
            return {"text": text, "mode": "live"}
        except Exception as e:
            return {"text": "", "error": str(e), "mode": "live"}
    return {"text": "Mock: voice input received. In live mode, Whisper transcribes your query.", "mode": "degraded"}


async def _extract_upload(content: bytes, fname: str) -> tuple[str, str | None]:
    """Convert one upload to reviewable text without writing to Cognee."""
    modality = _file_modality(fname)
    description = None
    extracted_text = ""
    if modality == "image":
        description = await describe_image(content, fname, _media_type_for(fname))
        extracted_text = f"IMAGE EVIDENCE — {fname}\n\nForensic description:\n{description}"
    elif modality == "audio":
        description = await transcribe_audio(content, fname)
        extracted_text = f"AUDIO TRANSCRIPT — {fname}\n\n{description}"
    elif modality == "video":
        description = await extract_video_description(content, fname)
        extracted_text = f"VIDEO EVIDENCE — {fname}\n\nFrame-by-frame forensic analysis:\n{description}"
    elif modality == "pdf":
        description = await extract_pdf_content(content, fname)
        extracted_text = f"PDF DOCUMENT — {fname}\n\n{description}"
    elif modality == "spreadsheet":
        description = await asyncio.to_thread(parse_spreadsheet, content, fname)
        extracted_text = description
    else:
        extracted_text = content.decode("utf-8", errors="ignore")
    return extracted_text, description


@app.post("/ingest-file/analyze")
async def analyze_ingest_file(file: UploadFile = File(...), context: str = Form("")):
    content = await file.read()
    fname = file.filename or "unknown"
    modality = _file_modality(fname)
    try:
        extracted_text, description = await _extract_upload(content, fname)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(502, f"Evidence analysis failed: {e}")
    if context.strip():
        extracted_text = (
            f"USER-PROVIDED SUBMISSION CONTEXT\n{context.strip()}\n\n"
            f"MODEL-GENERATED / EXTRACTED CONTENT — REVIEW BEFORE INGESTION\n{extracted_text}"
        )
    review_id = secrets.token_urlsafe(18)
    PENDING_INGESTIONS[review_id] = {
        "filename": fname, "size_bytes": len(content), "modality": modality,
        "extracted_text": extracted_text, "context": context.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "ok": True, "review_id": review_id, "filename": fname,
        "size_bytes": len(content), "type": modality, "description": description,
        "extracted_text": extracted_text, "context": context.strip(),
        "requires_confirmation": True, "mode": "live" if LIVE else "degraded",
    }


@app.post("/ingest-files/analyze")
async def analyze_ingest_files(
    files: list[UploadFile] = File(...),
    contexts: str = Form("[]"),
):
    """Analyze a batch with per-file results; one bad file never aborts its siblings."""
    from fastapi import HTTPException
    try:
        parsed_contexts = json.loads(contexts)
    except json.JSONDecodeError as e:
        raise HTTPException(422, f"contexts must be a JSON array: {e.msg}")
    if not isinstance(parsed_contexts, list) or len(parsed_contexts) != len(files):
        raise HTTPException(422, "contexts must contain one string for each file.")
    semaphore = asyncio.Semaphore(3)

    async def analyze_one(index: int, upload: UploadFile, supplied_context) -> dict:
        fname = upload.filename or f"file-{index + 1}"
        context = str(supplied_context or "").strip()
        modality = _file_modality(fname)
        try:
            async with semaphore:
                content = await upload.read()
                extracted_text, description = await _extract_upload(content, fname)
            if context:
                extracted_text = (
                    f"USER-PROVIDED SUBMISSION CONTEXT\n{context}\n\n"
                    f"MODEL-GENERATED / EXTRACTED CONTENT — REVIEW BEFORE INGESTION\n{extracted_text}"
                )
            review_id = secrets.token_urlsafe(18)
            PENDING_INGESTIONS[review_id] = {
                "filename": fname, "size_bytes": len(content), "modality": modality,
                "extracted_text": extracted_text, "context": context,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            return {"ok": True, "index": index, "review_id": review_id,
                    "filename": fname, "size_bytes": len(content), "type": modality,
                    "description": description, "extracted_text": extracted_text,
                    "context": context, "requires_confirmation": True}
        except Exception as e:
            return {"ok": False, "index": index, "filename": fname,
                    "error": f"Evidence analysis failed: {e}"}

    results = await asyncio.gather(*(
        analyze_one(i, upload, parsed_contexts[i]) for i, upload in enumerate(files)
    ))
    return {"ok": all(item["ok"] for item in results), "results": results,
            "mode": "live" if LIVE else "degraded"}


@app.post("/ingest-file/confirm")
async def confirm_ingest_file(req: ConfirmIngestReq):
    from fastapi import HTTPException
    pending = PENDING_INGESTIONS.get(req.review_id)
    if not pending:
        raise HTTPException(404, "Review not found or already confirmed.")
    reviewed_text = (req.extracted_text or pending["extracted_text"]).strip()
    if not reviewed_text:
        raise HTTPException(422, "Reviewed evidence text cannot be empty.")
    if req.context and req.context.strip() and req.context.strip() not in reviewed_text:
        reviewed_text = f"USER-VERIFIED CONTEXT\n{req.context.strip()}\n\n{reviewed_text}"
    if LIVE:
        await mem.remember(reviewed_text, dataset=DATASET)
    upload_id = f"evidence:upload-{len(UPLOADED_NODES) + 1}"
    UPLOADED_NODES.append({
        "id": upload_id,
        "label": pending["filename"],
        "type": "evidence",
        "modality": pending["modality"],
    })
    del PENDING_INGESTIONS[req.review_id]
    return {
        "ok": True,
        "filename": pending["filename"],
        "size_bytes": pending["size_bytes"],
        "dataset": DATASET,
        "mode": "live" if LIVE else "degraded",
        "type": pending["modality"],
        "graph_node_id": upload_id,
        "verified": True,
    }


@app.post("/ingest-files/confirm")
async def confirm_ingest_files(req: BatchConfirmIngestReq):
    """Confirm sequentially because Cognee's embedded graph writer is single-writer."""
    results = []
    for index, item in enumerate(req.items):
        try:
            result = await confirm_ingest_file(item)
            results.append({"ok": True, "index": index, **result})
        except Exception as e:
            detail = getattr(e, "detail", str(e))
            results.append({"ok": False, "index": index, "review_id": item.review_id,
                            "error": detail})
    return {"ok": all(item["ok"] for item in results), "results": results,
            "mode": "live" if LIVE else "degraded"}


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...)):
    """Compatibility route: text files still use analyze + immediate confirmation."""
    content = await file.read()
    fname = file.filename or "unknown"
    if _file_modality(fname) != "text":
        from fastapi import HTTPException
        raise HTTPException(409, "Non-text evidence must use analyze and confirm.")
    extracted_text, _ = await _extract_upload(content, fname)
    if LIVE and extracted_text:
        await mem.remember(extracted_text, dataset=DATASET)
    upload_id = f"evidence:upload-{len(UPLOADED_NODES) + 1}"
    UPLOADED_NODES.append({"id": upload_id, "label": fname, "type": "evidence", "modality": "text"})
    return {"ok": True, "filename": fname, "size_bytes": len(content), "dataset": DATASET,
            "mode": "live" if LIVE else "degraded", "type": "text", "graph_node_id": upload_id,
            "verified": True}
