"""
memory_service.py — the single abstraction over Cognee for ColdCache: Cold Case Connector.

Everything (FastAPI, demo, benchmark) goes through here so the rest of the codebase
never touches the raw SDK. All four lifecycle APIs live here:

    remember()  -> ingest case files / corpus into the knowledge graph
    recall()    -> query, with EXPLICIT graph-vs-vector modes (key for our benchmark)
    improve()   -> bridge a detective's in-session hunch into permanent memory
    forget()    -> expunge a sealed record (surgical subgraph deletion)

PRIORITY 0 STATUS: signatures below are VERIFIED against cognee source
(github.com/topoteretes/cognee, api/v1/*). The only thing still worth confirming on a
live keyed run is the runtime shape of recall()/search() results (list[RecallResponse])
so the benchmark's doc-id extraction maps cleanly — see docs/API_NOTES.md.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re as _re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import cognee

from backend.schema import ColdCaseGraph, COLD_CASE_EXTRACTION_PROMPT

# Cognee hardcodes a floor of 240 wall-clock seconds (see
# cognee.infrastructure.llm.retry_config.LLM_MIN_RETRY_SECONDS) before any structured-output
# LLM call is allowed to give up on rate-limit retries — several minutes longer than our own
# RECALL_TIMEOUT_S budget, so our Groq->local-Ollama fallback (_search_with_local_fallback /
# _cognify_with_local_fallback below) never got a chance to run; Groq's own retry loop ate the
# whole timeout window first. `llm_retry_stop_condition` is a shared tenacity `stop_all` object
# (`stop_after_attempt(2) & stop_after_delay(240)`) that every LLM adapter's `@retry(...)`
# decorator already captured by reference at import time, so reassigning the module attribute
# wouldn't reach the decorators — but mutating the *same* stop_after_delay instance's
# `.max_delay` in place does, since it's the identical object every decorated call consults.
try:
    from cognee.infrastructure.llm.retry_config import llm_retry_stop_condition as _cognee_retry_stop
    for _stop in getattr(_cognee_retry_stop, "stops", ()):
        if hasattr(_stop, "max_delay"):
            _stop.max_delay = float(os.getenv("COLDCACHE_LLM_RETRY_FLOOR_S", "8"))
except Exception:
    pass  # best-effort — if Cognee's internals change shape, just keep the library default.

# ---------------------------------------------------------------------------
# Recall response cache — keeps demo/judging reliable when the LLM provider is
# rate-limited (Groq's free tier is tight on TPM/TPD) by memoizing identical
# (mode, dataset, query) recalls on disk. First call for a given question is
# always live; repeats (e.g. a judge replaying the demo script, or the UI
# re-rendering) are instant and cost zero additional tokens. Set
# COLDCACHE_DISABLE_RECALL_CACHE=1 to force everything live (e.g. for grading
# "does the live call actually work" rather than cache hits).
_CACHE_PATH = Path(
    os.getenv("COLDCACHE_CACHE_DIR", "/tmp/hungover-coldcase/.cognee_data")
) / "recall_cache.json"
_cache_disabled = os.getenv("COLDCACHE_DISABLE_RECALL_CACHE", "").lower() in ("1", "true")
_recall_cache: dict[str, dict] | None = None


def _load_cache() -> dict[str, dict]:
    global _recall_cache
    if _recall_cache is not None:
        return _recall_cache
    try:
        _recall_cache = json.loads(_CACHE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        _recall_cache = {}
    return _recall_cache


def _save_cache() -> None:
    if _recall_cache is None:
        return
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(_recall_cache))
    except OSError:
        pass  # cache is best-effort; never block the request on a disk error


def _cache_key(mode: str, dataset: str, query: str) -> str:
    return hashlib.sha256(f"{mode}|{dataset}|{query.strip().lower()}".encode()).hexdigest()

# --- SearchType: verified export is `from cognee import SearchType` (re-exported from
# cognee.api.v1.search). Keep the defensive loop for older/newer layouts. ---
SearchType = None
for _path in (
    "cognee",                                   # from cognee import SearchType
    "cognee.api.v1.search",                     # older path
    "cognee.modules.search.types",              # newer path
):
    try:
        _mod = __import__(_path, fromlist=["SearchType"])
        SearchType = getattr(_mod, "SearchType")
        break
    except (ImportError, AttributeError):
        continue


class RecallMode(str, Enum):
    """The three retrievers we compare in the benchmark."""
    GRAPH = "graph"        # -> SearchType.GRAPH_COMPLETION   multi-hop traversal (our edge)
    VECTOR = "vector"      # -> SearchType.RAG_COMPLETION     Cognee's vector RAG
    INSIGHTS = "insights"  # -> SearchType.TRIPLET_COMPLETION relationships/triples
                           #    (NOTE: this cognee version has NO "INSIGHTS" member)


def _search_type_for(mode: RecallMode):
    """Map our modes to Cognee SearchType enum members (verified against source)."""
    if SearchType is None:
        return None
    # Verified member names from cognee SearchType enum. No INSIGHTS in this version →
    # TRIPLET_COMPLETION returns relationships/triples (closest to "insights").
    table = {
        RecallMode.GRAPH: "GRAPH_COMPLETION",
        RecallMode.VECTOR: "RAG_COMPLETION",
        RecallMode.INSIGHTS: "TRIPLET_COMPLETION",
    }
    return getattr(SearchType, table[mode])


@dataclass
class RecallResult:
    mode: str
    query: str
    answer: str                 # str() of whatever recall/search returns
    raw: Any                    # keep the raw object so we can inspect shape in smoke_test


DEFAULT_DATASET = "coldcases"
_triplet_ready_datasets: set[str] = set()
_triplet_locks: dict[str, asyncio.Lock] = {}


# ---------------------------------------------------------------------------
# 1. REMEMBER — ingest into permanent graph memory
# ---------------------------------------------------------------------------
async def remember(text: str, dataset: str = DEFAULT_DATASET) -> None:
    """Permanently structure text into the knowledge graph. Using add()+cognify() (rather
    than the high-level remember()) keeps dataset control and an explicit improve() beat
    for the demo. Both run synchronously by default, so the graph is ready on return."""
    await cognee.add(text, dataset_name=dataset)          # verified: add(data, dataset_name=...)
    await cognify(dataset)


async def remember_many(texts: list[str], dataset: str = DEFAULT_DATASET,
                        data_per_batch: int = 1, chunk_size: int = 1200) -> None:
    """Stage a document batch, then build it serially for small local LLMs."""
    await cognee.add(texts, dataset_name=dataset)
    await cognify(dataset, data_per_batch=data_per_batch, chunk_size=chunk_size)


async def _run_cognify(dataset: str, typed_schema: bool, data_per_batch: int, chunk_size):
    if typed_schema:
        await cognee.cognify(
            datasets=[dataset],
            graph_model=ColdCaseGraph,
            custom_prompt=COLD_CASE_EXTRACTION_PROMPT,
            data_per_batch=data_per_batch,
            chunk_size=chunk_size,
        )
    else:
        await cognee.cognify(
            datasets=[dataset], data_per_batch=data_per_batch, chunk_size=chunk_size
        )


async def cognify(dataset: str = DEFAULT_DATASET, typed_schema: bool = True,
                  data_per_batch: int = 20, chunk_size: int = None) -> None:
    """Build/refresh the graph. cognify() is synchronous by default (run_in_background=False)
    — it blocks until the graph is built, so no status polling is needed at our scale.

    typed_schema=True (default) passes our Cold Case Connector ontology (backend/schema.py)
    as cognify()'s `graph_model`, constraining extraction to explicit Person/Location/
    TimePoint/Evidence/Object nodes and WAS_AT/AT_TIME/DEPICTS/REPORTED_BY/CONTRADICTS edges
    instead of Cognee's free-form default KnowledgeGraph. Set False to fall back to default
    extraction (e.g. for A/B comparison or if the constrained schema needs loosening).

    Ingestion-time extraction hits a *different* Groq failure surface than recall()'s
    search-based calls: rather than rate-limit exceptions or degraded replies, Groq's small
    model occasionally emits invalid structured tool-call output (bad enum values, malformed
    function-call text) that exhausts Cognee/instructor's internal retries and raises a hard
    BadRequestError/RateLimitError. _cognify_with_local_fallback() catches that and retries
    once against local Ollama before giving up."""
    try:
        await _run_cognify(dataset, typed_schema, data_per_batch, chunk_size)
    except Exception as e:
        if not _using_groq_for_cognee():
            raise
        await _cognify_with_local_fallback(dataset, typed_schema, data_per_batch, chunk_size, str(e))
    _triplet_ready_datasets.discard(dataset)


async def _cognify_with_local_fallback(dataset: str, typed_schema: bool, data_per_batch: int,
                                       chunk_size, reason: str) -> None:
    """Swaps Cognee's global LLM config to local Ollama and retries cognify() once. Local
    models are typically *worse* than Groq at strict-schema tool calling, so if the typed
    (ColdCaseGraph) extraction fails again locally, we drop down to untyped free-form
    extraction as a last resort — better a loosely-typed graph than a hard ingest failure."""
    async with _llm_swap_lock:
        print(f"[fallback] Cognee/Groq cognify failed ({reason}) — retrying ingestion via local Ollama model")
        original = {
            "provider": os.getenv("LLM_PROVIDER"),
            "model": os.getenv("LLM_MODEL"),
            "endpoint": os.getenv("LLM_ENDPOINT"),
            "api_key": os.getenv("LLM_API_KEY"),
        }
        try:
            cognee.config.set_llm_provider("ollama")
            cognee.config.set_llm_model(os.getenv("OLLAMA_TEXT_MODEL", "llama3.1:8b"))
            cognee.config.set_llm_endpoint(os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1"))
            cognee.config.set_llm_api_key("ollama")
            try:
                await _run_cognify(dataset, typed_schema, data_per_batch, chunk_size)
            except Exception as local_typed_err:
                if not typed_schema:
                    raise
                print(f"[fallback] local typed-schema cognify also failed ({local_typed_err}) "
                      "— retrying with untyped extraction")
                await _run_cognify(dataset, False, data_per_batch, chunk_size)
        finally:
            # Always restore the original (Groq) config so the next request goes
            # back to the faster hosted provider rather than staying stuck local.
            if original["provider"] is not None:
                cognee.config.set_llm_provider(original["provider"])
            if original["model"] is not None:
                cognee.config.set_llm_model(original["model"])
            if original["endpoint"] is not None:
                cognee.config.set_llm_endpoint(original["endpoint"])
            if original["api_key"] is not None:
                cognee.config.set_llm_api_key(original["api_key"])


async def prepare_insights(dataset: str = DEFAULT_DATASET) -> None:
    """Build Cognee's triplet index once per dataset for TRIPLET_COMPLETION recall."""
    if dataset in _triplet_ready_datasets:
        return
    lock = _triplet_locks.setdefault(dataset, asyncio.Lock())
    async with lock:
        if dataset in _triplet_ready_datasets:
            return
        from cognee.memify_pipelines.create_triplet_embeddings import (
            create_triplet_embeddings,
        )
        from cognee.modules.users.methods import get_default_user

        await create_triplet_embeddings(user=await get_default_user(), dataset=dataset)
        _triplet_ready_datasets.add(dataset)


async def wait_for_indexing(dataset_ids: list, timeout_s: int = 300) -> None:
    """Only needed if you ingest with run_in_background=True. NOTE: cognee.datasets.get_status
    takes dataset *UUIDs*, not names → resolve names→ids first. Unused in the default
    synchronous flow above; kept for the large-corpus path."""
    get_status = getattr(getattr(cognee, "datasets", None), "get_status", None)
    if get_status is None:
        await asyncio.sleep(8)
        return
    waited = 0
    while waited < timeout_s:
        status = await get_status(dataset_ids)           # {id: {pipeline: status}}
        if "DATASET_PROCESSING_COMPLETED" in str(status) or "completed" in str(status).lower():
            return
        await asyncio.sleep(2)
        waited += 2


# ---------------------------------------------------------------------------
# 2. RECALL — query with EXPLICIT mode (this is what powers the 3-way benchmark)
# ---------------------------------------------------------------------------
def _extract_answer_text(raw: Any) -> str:
    """cognee.search()/recall() return shapes vary (list[str], or list[dict] with a
    'search_result' key holding the real answer text, e.g. [{'dataset_id': ..., 'dataset_name':
    ..., 'search_result': ['actual answer text']}]). Pull the human-readable text out instead
    of falling back to a raw dict repr, which used to leak straight into every endpoint's
    'answer'/'cognee_insight' field (chat, resolve, nexus, interrogation, whatif, report,
    suspect-timeline, recall, recall_compare all shared this bug)."""
    if not isinstance(raw, list):
        return str(raw)
    pieces: list[str] = []
    for item in raw:
        if isinstance(item, dict) and "search_result" in item:
            sr = item["search_result"]
            if isinstance(sr, list):
                pieces.extend(str(s) for s in sr)
            else:
                pieces.append(str(sr))
        elif isinstance(item, str):
            pieces.append(item)
        else:
            pieces.append(str(item))
    return "\n".join(pieces) if pieces else str(raw)


RECALL_TIMEOUT_S = float(os.getenv("COLDCACHE_RECALL_TIMEOUT_S", "25"))
# _search_with_local_fallback's own Groq attempt can now fail fast (~10-20s, thanks to the
# retry-floor monkeypatch above) but then still needs its own local-Ollama attempt afterward —
# wrapping the *whole* Groq-then-local sequence in the same RECALL_TIMEOUT_S budget as a plain
# single-provider call left no time for the local half to ever finish. This gives the combined
# sequence room for both phases while keeping the single-provider path just as fast as before.
FALLBACK_SEQUENCE_TIMEOUT_S = float(os.getenv("COLDCACHE_FALLBACK_TIMEOUT_S", "75"))
# CPU-only local Ollama inference is much slower than Groq's hosted hardware, and Cognee's
# search() makes MORE than one structured-output call per query when session memory is
# enabled by default (a "feedback_detection" turn-analysis call runs before the main search
# call) — both get routed to Ollama during the swap, so the local attempt alone needs a much
# larger timeout than the (fast, hosted) Groq attempt, or it gets cut off mid-inference.
LOCAL_FALLBACK_TIMEOUT_S = float(os.getenv("COLDCACHE_LOCAL_FALLBACK_TIMEOUT_S", "55"))

# ---------------------------------------------------------------------------
# Local-model auto-fallback — when Groq is rate-limited/out of quota, Cognee's
# own retries (via litellm) sometimes exhaust and return a low-effort/degraded
# reply ("Got it.", "Sure.", "OK.") instead of a real error, so a naive
# try/except around the search call alone isn't enough — we also have to
# detect a *degraded but "successful"* response and retry. When detected, we
# temporarily swap Cognee's global LLM config to a local Ollama model, redo
# the same search call, then restore the original Groq config — serialized
# behind a lock since Cognee's LLM config is process-global, not per-call.
# ---------------------------------------------------------------------------
_llm_swap_lock = asyncio.Lock()
_DEGRADED_ANSWER_RE = _re.compile(
    r"^\s*(got it|sure|ok(ay)?|noted|understood|i (understand|see)|alright|will do)\.?\s*$",
    _re.IGNORECASE,
)


def _is_degraded_answer(text: str) -> bool:
    """Heuristic for a low-effort acknowledgment-only reply — Cognee's usual symptom
    when the underlying LLM call got starved by a Groq rate limit mid-retry but didn't
    raise a clean exception. Real answers are never this short/generic."""
    return bool(text) and len(text) < 40 and bool(_DEGRADED_ANSWER_RE.match(text.strip()))


def _using_groq_for_cognee() -> bool:
    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    endpoint = (os.getenv("LLM_ENDPOINT") or "").lower()
    return provider == "custom" and "groq.com" in endpoint


async def _search_with_local_fallback(query_text: str, query_type, datasets: list[str]):
    """Runs cognee.search(), and if Groq errored or returned a degraded/empty answer,
    retries once against a local Ollama model (default llama3.1:8b — already used
    elsewhere in this repo for the offline-Ollama option, see .env.example)."""
    try:
        raw = await cognee.search(query_text=query_text, query_type=query_type, datasets=datasets)
        answer_preview = _extract_answer_text(raw)
        if not _is_degraded_answer(answer_preview):
            return raw, False
        reason = f"degraded reply ({answer_preview!r})"
    except Exception as e:
        reason = str(e)

    if not _using_groq_for_cognee():
        # Not routed through Groq in the first place (or already local) — nothing
        # to fall back to; surface the original failure/degraded result untouched.
        raise RuntimeError(reason)

    async with _llm_swap_lock:
        print(f"[fallback] Cognee/Groq unavailable ({reason}) — retrying via local Ollama model")
        original = {
            "provider": os.getenv("LLM_PROVIDER"),
            "model": os.getenv("LLM_MODEL"),
            "endpoint": os.getenv("LLM_ENDPOINT"),
            "api_key": os.getenv("LLM_API_KEY"),
        }
        try:
            cognee.config.set_llm_provider("ollama")
            cognee.config.set_llm_model(os.getenv("OLLAMA_TEXT_MODEL", "llama3.1:8b"))
            cognee.config.set_llm_endpoint(os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1"))
            cognee.config.set_llm_api_key("ollama")
            raw = await asyncio.wait_for(
                cognee.search(query_text=query_text, query_type=query_type, datasets=datasets),
                timeout=LOCAL_FALLBACK_TIMEOUT_S,
            )
            return raw, True
        finally:
            # Always restore the original (Groq) config so the next request goes
            # back to the faster hosted provider rather than staying stuck local.
            if original["provider"] is not None:
                cognee.config.set_llm_provider(original["provider"])
            if original["model"] is not None:
                cognee.config.set_llm_model(original["model"])
            if original["endpoint"] is not None:
                cognee.config.set_llm_endpoint(original["endpoint"])
            if original["api_key"] is not None:
                cognee.config.set_llm_api_key(original["api_key"])


async def recall(query: str, mode: RecallMode = RecallMode.GRAPH,
                 dataset: str = DEFAULT_DATASET) -> RecallResult:
    key = _cache_key(mode.value, dataset, query)
    if not _cache_disabled:
        cached = _load_cache().get(key)
        if cached is not None:
            return RecallResult(mode=mode.value, query=query, answer=cached["answer"], raw=cached["answer"])

    if mode == RecallMode.INSIGHTS:
        await prepare_insights(dataset)
    st = _search_type_for(mode)
    try:
        if st is not None:
            # verified: search(query_text, query_type=SearchType, datasets=[names]).
            # _search_with_local_fallback wraps this with the Groq-rate-limit ->
            # local Ollama auto-switch (see its docstring above).
            raw, used_fallback = await asyncio.wait_for(
                _search_with_local_fallback(query, st, [dataset]),
                timeout=FALLBACK_SEQUENCE_TIMEOUT_S,
            )
        else:
            # High-level auto-routing fallback if SearchType didn't import.
            raw = await asyncio.wait_for(
                cognee.recall(query_text=query, datasets=[dataset]),
                timeout=RECALL_TIMEOUT_S,
            )
            used_fallback = False
    except asyncio.TimeoutError:
        # The LLM provider (Groq free tier) can be rate-limited and retries internally for
        # minutes; capping our own wait means the UI always gets a fast, honest response
        # instead of hanging through a live demo. Not cached — a real retry should succeed
        # once the provider's per-minute window rolls over.
        answer = (
            "The knowledge graph is temporarily busy (the LLM provider is rate-limited) — "
            "please retry this question in about a minute."
        )
        return RecallResult(mode=mode.value, query=query, answer=answer, raw=None)
    except Exception:
        # _search_with_local_fallback already tried Groq, then local Ollama (if
        # configured) and still failed both — surface the same friendly message
        # rather than a raw stack trace reaching the UI.
        answer = (
            "The knowledge graph is temporarily busy (the LLM provider is rate-limited) — "
            "please retry this question in about a minute."
        )
        return RecallResult(mode=mode.value, query=query, answer=answer, raw=None)
    answer = _extract_answer_text(raw)

    if not _cache_disabled:
        cache = _load_cache()
        cache[key] = {"answer": answer, "cached_at": time.time()}
        _save_cache()

    return RecallResult(mode=mode.value, query=query, answer=answer, raw=raw)


# ---------------------------------------------------------------------------
# 3. IMPROVE — bridge an in-session detective hunch into permanent memory
# ---------------------------------------------------------------------------
async def log_hunch(text: str, session_id: str, dataset: str = DEFAULT_DATASET) -> None:
    """A detective's mid-investigation note: lives in SESSION memory only (not yet
    part of the permanent graph) until the case resolves."""
    # verified: remember(data, *, session_id=..., self_improvement=...) — session_id routes
    # the entry into session memory; self_improvement=False keeps it out of auto-improve.
    await cognee.remember(text, session_id=session_id, self_improvement=False)

async def resolve_case(session_ids: list[str], dataset: str = DEFAULT_DATASET) -> None:
    """On case resolution, improve() bridges the session hunches into the permanent
    graph and re-weights connections. Per docs, improve() only does real work when
    given session_ids — that's the whole point of this flow."""
    await cognee.improve(dataset=dataset, session_ids=session_ids)   # verified signature


# ---------------------------------------------------------------------------
# 4. FORGET — expunge a sealed record (surgical deletion)
# ---------------------------------------------------------------------------
async def expunge(dataset: str) -> None:
    """Legal record expungement: surgically remove a dataset's subgraph while leaving
    everything else intact. The showstopper demo for forget()."""
    await cognee.forget(dataset=dataset)                              # verified signature


# Convenience for a clean slate during dev.
async def reset_all() -> None:
    prune = getattr(cognee, "prune", None)
    if prune is not None:
        # verified: cognee.prune.prune_data() and cognee.prune.prune_system(...)
        prune_data = getattr(prune, "prune_data", None)
        prune_system = getattr(prune, "prune_system", None)
        if prune_data:
            await prune_data()
        if prune_system:
            await prune_system(metadata=True)
