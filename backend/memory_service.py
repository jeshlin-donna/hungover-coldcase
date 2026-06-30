"""
memory_service.py — the single abstraction over Cognee for HungOver: Cold Case Connector.

Everything (FastAPI, demo, benchmark) goes through here so the rest of the codebase
never touches the raw SDK. All four lifecycle APIs live here:

    remember()  -> ingest case files / corpus into the knowledge graph
    recall()    -> query, with EXPLICIT graph-vs-vector modes (key for our benchmark)
    improve()   -> bridge a detective's in-session hunch into permanent memory
    forget()    -> expunge a sealed record (surgical subgraph deletion)

IMPORTANT (Priority 0): A few SDK details below are marked  # VERIFY  — they are
inferred from the docs. Run backend/smoke_test.py on a real machine FIRST, then pin
the exact import paths / return shapes here and in docs/API_NOTES.md.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import cognee

# --- SearchType import is version-dependent; resolve defensively. # VERIFY ---
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
    GRAPH = "graph"        # SearchType.GRAPH_COMPLETION  -> multi-hop traversal (our edge)
    VECTOR = "vector"      # SearchType.RAG_COMPLETION    -> Cognee's vector RAG
    INSIGHTS = "insights"  # SearchType.INSIGHTS          -> raw relationships (great for graph viz)


def _search_type_for(mode: RecallMode):
    """Map our modes to Cognee SearchType enum members.  # VERIFY enum member names."""
    if SearchType is None:
        return None
    table = {
        RecallMode.GRAPH: "GRAPH_COMPLETION",
        RecallMode.VECTOR: "RAG_COMPLETION",
        RecallMode.INSIGHTS: "INSIGHTS",
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
    """Permanently structure text into the knowledge graph (low-level add+cognify
    gives us dataset control + async indexing, which the demo/benchmark need)."""
    await cognee.add(text, dataset_name=dataset)          # # VERIFY kwarg name
    await cognify(dataset)


async def cognify(dataset: str = DEFAULT_DATASET) -> None:
    """Build/refresh the graph for a dataset, then wait until it's actually indexed."""
    await cognee.cognify(datasets=[dataset])              # # VERIFY: datasets= vs positional
    await wait_for_indexing(dataset)


async def wait_for_indexing(dataset: str = DEFAULT_DATASET, timeout_s: int = 300) -> None:
    """Poll real indexing status instead of a blind sleep (Technical Excellence).
    # VERIFY the actual status API + the 'completed' sentinel in smoke_test."""
    get_status = getattr(getattr(cognee, "datasets", None), "get_status", None)
    if get_status is None:
        # Fallback if the status API isn't exposed in this version.
        await asyncio.sleep(8)
        return
    waited = 0
    while waited < timeout_s:
        status = await get_status([dataset])             # # VERIFY arg + return shape
        s = str(status).lower()
        if "complet" in s or "finish" in s or "indexed" in s:
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
        raw = await cognee.search(query_text=query, query_type=st)   # # VERIFY kwargs
    else:
        # High-level auto-routing fallback if SearchType didn't import.
        raw = await cognee.recall(query_text=query)                  # # VERIFY kwarg
    return RecallResult(mode=mode.value, query=query, answer=str(raw), raw=raw)


# ---------------------------------------------------------------------------
# 3. IMPROVE — bridge an in-session detective hunch into permanent memory
# ---------------------------------------------------------------------------
async def log_hunch(text: str, session_id: str, dataset: str = DEFAULT_DATASET) -> None:
    """A detective's mid-investigation note: lives in SESSION memory only (not yet
    part of the permanent graph) until the case resolves."""
    await cognee.remember(text, session_id=session_id, self_improvement=False)  # # VERIFY

async def resolve_case(session_ids: list[str], dataset: str = DEFAULT_DATASET) -> None:
    """On case resolution, improve() bridges the session hunches into the permanent
    graph and re-weights connections. Per docs, improve() only does real work when
    given session_ids — that's the whole point of this flow."""
    await cognee.improve(dataset=dataset, session_ids=session_ids)   # # VERIFY


# ---------------------------------------------------------------------------
# 4. FORGET — expunge a sealed record (surgical deletion)
# ---------------------------------------------------------------------------
async def expunge(dataset: str) -> None:
    """Legal record expungement: surgically remove a dataset's subgraph while leaving
    everything else intact. The showstopper demo for forget()."""
    await cognee.forget(dataset=dataset)                              # # VERIFY


# Convenience for a clean slate during dev.
async def reset_all() -> None:
    prune = getattr(cognee, "prune", None)
    if prune is not None:
        # # VERIFY: prune may expose prune_data() / prune_system()
        for fn in ("prune_data", "prune_system"):
            f = getattr(prune, fn, None)
            if f:
                await f()
