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
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

_anthropic_client = None
_groq_client = None
_ollama_client = None
_ollama_reachable_cache: dict = {"ok": False, "checked_at": 0.0}
FALLBACK_STATE = {"active": False, "last_reason": None, "last_at": None}

VISION_PROMPT = (
    "You are analyzing evidence for a cold case investigation. "
    "Image filename: {filename}\n\n"
    "Describe this image in forensic detail. Note: any visible people "
    "(physical description, clothing, distinguishing features), vehicles "
    "(make, model, color, license plates), locations or addresses, objects "
    "of interest, any visible text or timestamps, and anything potentially "
    "relevant to a criminal investigation. Be specific and factual."
)


def _using_groq() -> bool:
    """True when LLM_PROVIDER/LLM_ENDPOINT are configured to point at Groq's
    OpenAI-compatible API — lets us route vision + transcription through Groq
    too instead of Anthropic/local Whisper, using the same single LLM_API_KEY."""
    import os

    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    endpoint = (os.getenv("LLM_ENDPOINT") or "").lower()
    return provider == "groq" or "groq.com" in endpoint


def _get_groq_client():
    """Lazily construct and cache an OpenAI-SDK client pointed at Groq's
    OpenAI-compatible endpoint (avoids reconnecting per-request)."""
    global _groq_client
    if _groq_client is None:
        import os
        from openai import OpenAI

        _groq_client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_ENDPOINT") or "https://api.groq.com/openai/v1",
        )
    return _groq_client


def _get_anthropic_client():
    """Lazily construct and cache the Anthropic client (avoids reconnecting per-request)."""
    global _anthropic_client
    if _anthropic_client is None:
        import os
        import anthropic as ant

        _anthropic_client = ant.Anthropic(api_key=os.getenv("LLM_API_KEY"))
    return _anthropic_client


def _get_ollama_client():
    """Lazily construct and cache an OpenAI-SDK client pointed at a local Ollama
    server's OpenAI-compatible endpoint — this is the offline fallback used when
    Groq is rate-limited/out of quota, so multimodal ingestion never hard-fails
    mid-demo. Requires `ollama serve` running + the model pulled (see .env.example)."""
    global _ollama_client
    if _ollama_client is None:
        import os
        from openai import OpenAI

        _ollama_client = OpenAI(
            api_key="ollama",  # unused by Ollama, but required by the SDK
            base_url=os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        )
    return _ollama_client


def _ollama_reachable() -> bool:
    """Cheap, short-TTL-cached reachability probe for the local Ollama server.
    Avoids paying a multi-second connect timeout on every single fallback call
    when Ollama isn't running — but re-checks every 30s in case it comes up."""
    import os
    import time
    import urllib.request

    now = time.monotonic()
    if now - _ollama_reachable_cache["checked_at"] < 30:
        return _ollama_reachable_cache["ok"]

    endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1")
    try:
        urllib.request.urlopen(f"{endpoint}/models", timeout=1.5)
        _ollama_reachable_cache["ok"] = True
    except Exception:
        _ollama_reachable_cache["ok"] = False
    _ollama_reachable_cache["checked_at"] = now
    return _ollama_reachable_cache["ok"]


def _note_fallback(reason: str) -> None:
    """Record that we just fell back to a local model, so /health can surface
    it in the UI (stats ribbon / status) instead of it being a silent swap."""
    import datetime

    FALLBACK_STATE["active"] = True
    FALLBACK_STATE["last_reason"] = reason
    FALLBACK_STATE["last_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    print(f"[fallback] Groq unavailable ({reason}) — switched to local model for this request")


async def describe_image(content: bytes, filename: str, media_type: str) -> str:
    """Send image to a vision LLM and get a forensic description for Cognee ingestion.
    Routes to Groq's vision model when configured; if Groq errors (rate limit, quota
    exhausted, network issue, etc.) it automatically falls back to a local Ollama vision
    model (moondream) so ingestion never hard-fails mid-demo, then Claude as a last resort."""
    b64 = base64.standard_b64encode(content).decode()
    prompt_text = VISION_PROMPT.format(filename=filename)

    if _using_groq():
        try:
            return await _describe_image_groq(b64, media_type, prompt_text)
        except Exception as e:
            _note_fallback(f"vision: {e}")
            local = await _describe_image_local(b64, media_type, prompt_text)
            if local is not None:
                return local
            try:
                return await _describe_image_claude(b64, media_type, prompt_text)
            except Exception:
                return f"[Vision unavailable — Groq failed ({e}) and no local/Claude fallback succeeded]"

    return await _describe_image_claude(b64, media_type, prompt_text)


async def _describe_image_groq(b64: str, media_type: str, prompt_text: str) -> str:
    import os

    client = _get_groq_client()
    model = os.getenv("LLM_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    def _call():
        # Groq's SDK (OpenAI-compatible) is synchronous/blocking; run it off the
        # event loop thread so a slow vision call doesn't stall every other
        # concurrent request (health checks, /recall, other uploads, ...).
        return client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{b64}"
                    }},
                ],
            }],
        )

    resp = await asyncio.to_thread(_call)
    return resp.choices[0].message.content


async def _describe_image_local(b64: str, media_type: str, prompt_text: str) -> str | None:
    """Offline vision fallback via a local Ollama model (default: moondream — small,
    fast, vision-capable). Returns None (not an exception) if Ollama isn't reachable,
    so the caller can cleanly move on to the next fallback in the chain."""
    import os

    if not _ollama_reachable():
        return None
    client = _get_ollama_client()
    model = os.getenv("OLLAMA_VISION_MODEL", "moondream")

    def _call():
        return client.chat.completions.create(
            model=model,
            max_tokens=768,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{b64}"
                    }},
                ],
            }],
        )

    try:
        resp = await asyncio.to_thread(_call)
        return resp.choices[0].message.content
    except Exception:
        return None


async def _describe_image_claude(b64: str, media_type: str, prompt_text: str) -> str:
    client = _get_anthropic_client()

    def _call():
        # anthropic's SDK is synchronous/blocking; run it off the event loop thread
        # so a slow vision call doesn't stall every other concurrent request
        # (health checks, /recall, other uploads, ...).
        return client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                                                  "media_type": media_type,
                                                  "data": b64}},
                    {"type": "text", "text": prompt_text}
                ]
            }]
        )

    msg = await asyncio.to_thread(_call)
    return msg.content[0].text


_whisper_model = None


def _get_whisper_model():
    """Lazily load and cache the Whisper model — loading weights from disk on every
    request (the previous behavior) added seconds of latency to every audio upload."""
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model("tiny")
    return _whisper_model


async def transcribe_audio(content: bytes, filename: str) -> str:
    """Transcribe audio to text. Uses Groq's hosted Whisper API when configured
    (faster, no local model download needed); automatically falls back to local
    Whisper (tiny model) if Groq errors (rate limit, quota exhausted, network, etc.)
    or if Groq isn't configured at all."""
    if _using_groq():
        try:
            return await _transcribe_audio_groq(content, filename)
        except Exception as e:
            _note_fallback(f"audio: {e}")
            return await _transcribe_audio_local(content, filename)

    return await _transcribe_audio_local(content, filename)


async def _transcribe_audio_groq(content: bytes, filename: str) -> str:
    import os

    client = _get_groq_client()
    model = os.getenv("LLM_TRANSCRIPTION_MODEL", "whisper-large-v3")
    suffix = Path(filename).suffix or ".mp3"

    def _call():
        # Groq's SDK is synchronous/blocking; run it off the event loop thread.
        return client.audio.transcriptions.create(
            model=model,
            file=(f"audio{suffix}", content),
        )

    resp = await asyncio.to_thread(_call)
    return (resp.text or "").strip()


async def _transcribe_audio_local(content: bytes, filename: str) -> str:
    import tempfile, os
    try:
        import whisper  # noqa: F401  (import check only; loading is cached separately)
    except ImportError:
        return "[Audio transcription unavailable: pip install openai-whisper]"
    suffix = Path(filename).suffix or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        def _transcribe():
            # Whisper's load + transcribe are both CPU-bound and blocking; run them
            # in a worker thread so the event loop stays free for other requests.
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

# --- Case label: either a manual override (set via POST /case-name) or an
# LLM-auto-generated short label derived from the ingested evidence itself,
# regenerated only when the evidence set actually changes (cheap to poll). ---
CASE_LABEL_OVERRIDE: str | None = None
_case_label_cache: dict = {"label": None, "upload_count": -1}

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


# --- routes (match API_CONTRACT.md) ------------------------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "mode": "live" if LIVE else "degraded",
        "fallback": FALLBACK_STATE,
    }


async def _get_case_label() -> str:
    """Resolve the case label shown in the stats ribbon: a manual override (set via
    POST /case-name) always wins; otherwise, once there's real ingested evidence, ask
    the LLM for a short label derived from it (e.g. "Daniel Marsh · Millbrook /
    Riverside") — cached and only regenerated when the evidence set actually grows,
    so this doesn't fire an LLM call on every single /graph poll."""
    if CASE_LABEL_OVERRIDE:
        return CASE_LABEL_OVERRIDE

    if not UPLOADED_NODES:
        # No user-uploaded evidence yet — the curated hero-case graph (Daniel Marsh)
        # is always pre-loaded as the reliable default demo scenario, so show its
        # real name rather than a misleading "awaiting evidence" placeholder.
        return "Daniel Marsh · Millbrook / Riverside"

    if _case_label_cache["upload_count"] == len(UPLOADED_NODES) and _case_label_cache["label"]:
        return _case_label_cache["label"]

    if LIVE:
        try:
            res = await mem.recall(
                "In 6 words or fewer, give a short case label in the exact format "
                "'PrimaryName · LocationA / LocationB' (or just 'PrimaryName' if there's "
                "only one location) based on the suspect/victim and place names in this "
                "evidence. Return ONLY the label, nothing else — no punctuation-free "
                "explanation, no quotes.",
                mode=mem.RecallMode.GRAPH,
                dataset=DATASET,
            )
            # res.raw is None specifically when recall() hit its timeout/failure sentinel
            # (rate-limited/degraded, both Groq and local fallback exhausted) — that path
            # returns a "temporarily busy" string as res.answer without raising, so it must
            # be checked explicitly or the friendly error text gets cached as the case name.
            label = res.answer.strip().strip('"').split("\n")[0][:80]
            if label and res.raw is not None:
                _case_label_cache["label"] = label
                _case_label_cache["upload_count"] = len(UPLOADED_NODES)
                return label
        except Exception:
            pass

    return f"Untitled Case — {len(UPLOADED_NODES)} file(s) ingested"


@app.get("/case-name")
async def get_case_name():
    return {"label": await _get_case_label(), "manual": CASE_LABEL_OVERRIDE is not None}


class CaseNameBody(BaseModel):
    label: str | None = None  # None/empty clears the override, reverting to auto-label


@app.post("/case-name")
async def set_case_name(body: CaseNameBody):
    global CASE_LABEL_OVERRIDE
    CASE_LABEL_OVERRIDE = (body.label or "").strip() or None
    return {"label": await _get_case_label(), "manual": CASE_LABEL_OVERRIDE is not None}


@functools.lru_cache(maxsize=1)
def hero_case_doc_count() -> int:
    """Real file count of the pre-loaded hero-case corpus (data/hero_case/*) — the
    honest floor for 'docs ingested' since that corpus is always in the graph by
    default, independent of anything the user uploads via Messy Desk this session."""
    return sum(1 for _ in HERO.glob("*") if _.is_file())


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
    payload["docs_ingested"] = hero_case_doc_count() + len(UPLOADED_NODES)
    payload["case_label"] = await _get_case_label()
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
    res = await mem.recall(req.message, mode=mem.RecallMode.GRAPH, dataset=DATASET)
    sources = extract_ids(str(res.raw), known_doc_ids())[:5]
    return {"answer": res.answer, "sources": sources, "mode": "live"}


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


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...)):
    content = await file.read()
    fname = file.filename or "unknown"
    modality = _file_modality(fname)
    extracted_text = None
    description = None

    if modality == "image":
        media_type = _media_type_for(fname)
        if LIVE:
            try:
                description = await describe_image(content, fname, media_type)
                extracted_text = f"IMAGE EVIDENCE — {fname}\n\nForensic description:\n{description}"
            except Exception as e:
                description = f"[Vision analysis failed: {e}]"
        else:
            description = "Mock mode: image received. Live mode uses Claude vision to extract a forensic description."

    elif modality == "audio":
        if LIVE:
            try:
                transcript = await transcribe_audio(content, fname)
                description = transcript
                extracted_text = f"AUDIO TRANSCRIPT — {fname}\n\n{transcript}"
            except Exception as e:
                description = f"[Transcription failed: {e}]"
        else:
            description = "Mock mode: audio received. Live mode uses Whisper to transcribe and ingest the transcript."

    elif modality == "video":
        if LIVE:
            try:
                description = await extract_video_description(content, fname)
                extracted_text = f"VIDEO EVIDENCE — {fname}\n\nFrame-by-frame forensic analysis:\n{description}"
            except Exception as e:
                description = f"[Video analysis failed: {e}]"
        else:
            description = "Mock mode: video received. Live mode extracts keyframes and describes each with Claude vision."

    elif modality == "pdf":
        if LIVE:
            try:
                description = await extract_pdf_content(content, fname)
                extracted_text = f"PDF DOCUMENT — {fname}\n\n{description}"
            except Exception as e:
                description = f"[PDF extraction failed: {e}]"
        else:
            description = "Mock mode: PDF received. Live mode extracts text (or uses vision for scanned pages)."

    elif modality == "spreadsheet":
        description = await asyncio.to_thread(parse_spreadsheet, content, fname)
        extracted_text = description

    else:
        extracted_text = content.decode("utf-8", errors="ignore")

    if LIVE and extracted_text:
        await mem.remember(extracted_text, dataset=DATASET)

    upload_id = f"evidence:upload-{len(UPLOADED_NODES) + 1}"
    UPLOADED_NODES.append({
        "id": upload_id,
        "label": fname,
        "type": "evidence",
        "modality": modality,
    })

    return {
        "ok": True,
        "filename": fname,
        "size_bytes": len(content),
        "dataset": DATASET,
        "mode": "live" if LIVE else "degraded",
        "type": modality,
        "description": description,
        "graph_node_id": upload_id,
    }
