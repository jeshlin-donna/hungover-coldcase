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
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import cognee

from backend.schema import ColdCaseGraph, COLD_CASE_EXTRACTION_PROMPT

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


# ---------------------------------------------------------------------------
# 1. REMEMBER — ingest into permanent graph memory
# ---------------------------------------------------------------------------
async def remember(text: str, dataset: str = DEFAULT_DATASET) -> None:
    """Permanently structure text into the knowledge graph. Using add()+cognify() (rather
    than the high-level remember()) keeps dataset control and an explicit improve() beat
    for the demo. Both run synchronously by default, so the graph is ready on return."""
    await cognee.add(text, dataset_name=dataset)          # verified: add(data, dataset_name=...)
    await cognify(dataset)


async def cognify(dataset: str = DEFAULT_DATASET, typed_schema: bool = True) -> None:
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
        )
    else:
        await cognee.cognify(datasets=[dataset])          # verified: cognify(datasets=[...])


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
async def recall(query: str, mode: RecallMode = RecallMode.GRAPH,
                 dataset: str = DEFAULT_DATASET) -> RecallResult:
    st = _search_type_for(mode)
    if st is not None:
        # verified: search(query_text, query_type=SearchType, datasets=[names])
        raw = await cognee.search(query_text=query, query_type=st, datasets=[dataset])
    else:
        # High-level auto-routing fallback if SearchType didn't import.
        raw = await cognee.recall(query_text=query, datasets=[dataset])
    # recall()/search() return list[RecallResponse]; stringify defensively for display.
    answer = "\n".join(str(x) for x in raw) if isinstance(raw, list) else str(raw)
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
