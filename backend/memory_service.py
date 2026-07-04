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
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import cognee

from backend.schema import ColdCaseGraph, COLD_CASE_EXTRACTION_PROMPT

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


async def cognify(dataset: str = DEFAULT_DATASET, typed_schema: bool = True,
                  data_per_batch: int = 20, chunk_size: int = None) -> None:
    """Build/refresh the graph. cognify() is synchronous by default (run_in_background=False)
    — it blocks until the graph is built, so no status polling is needed at our scale.

    typed_schema=True (default) passes our Cold Case Connector ontology (backend/schema.py)
    as cognify()'s `graph_model`, constraining extraction to explicit Person/Location/
    TimePoint/Evidence/Object nodes and WAS_AT/AT_TIME/DEPICTS/REPORTED_BY/CONTRADICTS edges
    instead of Cognee's free-form default KnowledgeGraph. Set False to fall back to default
    extraction (e.g. for A/B comparison or if the constrained schema needs loosening)."""
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
    _triplet_ready_datasets.discard(dataset)


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
            # verified: search(query_text, query_type=SearchType, datasets=[names])
            raw = await asyncio.wait_for(
                cognee.search(query_text=query, query_type=st, datasets=[dataset]),
                timeout=RECALL_TIMEOUT_S,
            )
        else:
            # High-level auto-routing fallback if SearchType didn't import.
            raw = await asyncio.wait_for(
                cognee.recall(query_text=query, datasets=[dataset]),
                timeout=RECALL_TIMEOUT_S,
            )
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
