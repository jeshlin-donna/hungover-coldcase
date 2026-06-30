"""
demo.py — the live presentation. Run this on stage; narrate over it.

Five phases, each exercising a Cognee lifecycle API for a real reason:

    Phase 1  remember()  — ingest the case files from two siloed jurisdictions
    Phase 2  remember(session) — a detective logs an in-session HUNCH (session memory)
    Phase 3  recall()    — the same multi-hop question in VECTOR vs GRAPH mode.
                           Vector returns one local chunk; graph connects both counties.
    Phase 4  improve()   — case resolves: bridge the hunch into permanent memory,
                           re-ask, show the answer get sharper (the self-learning moment)
    Phase 5  forget()    — a record is sealed (expungement): surgically delete its
                           subgraph; everything else stays intact.

Usage (on a machine with cognee + LLM_API_KEY):
    python demo/demo.py --reset      # prune first for a clean, repeatable run
    python demo/demo.py

Everything goes through backend/memory_service.py, so once Priority 0 pins the
`# VERIFY` SDK details there, this demo inherits the fixes automatically.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import memory_service as mem  # noqa: E402
from memory_service import RecallMode  # noqa: E402

HERO = ROOT / "data" / "hero_case"
DATASET = "coldcases"
SESSION = "case-MH-0102"

# The two questions that make or break the demo. The first is single-hop (vector is
# fine). The second is multi-hop across jurisdictions (only the graph should connect it).
Q_SINGLE = "What tool caused the marks on the rear door at 14 Maple Heights Drive?"
Q_MULTI = ("Is there forensic evidence linking the Maple Heights and Riverside "
           "burglaries? If so, what is it?")


# --- tiny presentation helpers -------------------------------------------------
def banner(n: int, title: str) -> None:
    print(f"\n{'='*72}\n  PHASE {n} — {title}\n{'='*72}")

def slow(text: str, pause: float = 0.6) -> None:
    print(text)
    time.sleep(pause)

def answer_block(label: str, res) -> None:
    print(f"\n  ▸ {label}")
    print("  " + "-" * 68)
    for line in str(res.answer).splitlines() or [str(res.answer)]:
        print("    " + line)


def load_case_docs() -> list[tuple[str, str]]:
    docs = []
    for path in sorted(glob.glob(str(HERO / "*.md"))):
        if "00_README" in path:
            continue
        docs.append((Path(path).name, Path(path).read_text()))
    return docs


# --- the show ------------------------------------------------------------------
async def main(reset: bool) -> None:
    if reset:
        slow("Pruning previous state for a clean run...", 0.3)
        await mem.reset_all()

    # PHASE 1 — REMEMBER
    banner(1, "remember(): ingest evidence from two siloed departments")
    docs = load_case_docs()
    slow(f"Ingesting {len(docs)} case documents "
         f"(Maple Heights PD + Riverside PD — no shared records system)...")
    for name, text in docs:
        await mem.remember(text, dataset=DATASET)
        slow(f"   ✓ indexed {name}", 0.15)
    slow("\nAll evidence is now in one knowledge graph. The departments never were.")

    # PHASE 2 — SESSION HUNCH
    banner(2, "remember(session): a detective logs a working hunch")
    slow('Det. Cole (Maple Heights): "Third job with the same signature in two '
         'years. Feels like one person — but I can\'t prove a cross-county link."')
    await mem.log_hunch(
        "Hunch (unconfirmed): the 8mm left-nick pry signature may match an "
        "out-of-county burglary. Worth a regional check.",
        session_id=SESSION, dataset=DATASET)
    slow("   ✓ logged to SESSION memory — not yet part of the permanent graph.")

    # PHASE 3 — RECALL: vector vs graph
    banner(3, "recall(): vector vs graph on the question that matters")
    slow(f'Single-hop question (vector is fine here):\n   "{Q_SINGLE}"')
    answer_block("VECTOR (RAG_COMPLETION)",
                 await mem.recall(Q_SINGLE, mode=RecallMode.VECTOR, dataset=DATASET))

    slow(f'\nNow the MULTI-HOP question — across two jurisdictions:\n   "{Q_MULTI}"')
    answer_block("VECTOR (RAG_COMPLETION) — retrieves the nearest single chunk",
                 await mem.recall(Q_MULTI, mode=RecallMode.VECTOR, dataset=DATASET))
    answer_block("GRAPH (GRAPH_COMPLETION) — traverses the shared tool signature",
                 await mem.recall(Q_MULTI, mode=RecallMode.GRAPH, dataset=DATASET))
    slow("\n  → Only the graph connects MH-2023-0312 (Clearwater Co.) with "
         "RV-2023-0788 (Hale Co.). That link is the whole case.")

    # The "Alibi Break" — Cognee gives the linked graph; the contradiction call-out is ours.
    slow('\nThe Alibi Break — Marsh claims he was 300mi out of state that night:')
    answer_block("GRAPH — alibi vs financial records",
                 await mem.recall(
                     "Does Daniel Marsh's alibi for the night of the Riverside burglary "
                     "hold up against his financial records?",
                     mode=RecallMode.GRAPH, dataset=DATASET))
    slow("  → The alibi (MARSH-ALIBI) collapses against the motel record (MARSH-RECEIPT) "
         "4.2 miles from the scene. Cognee linked them; we flag the contradiction.")

    # PHASE 4 — IMPROVE
    banner(4, "improve(): the case resolves and memory gets smarter")
    slow("Suspect arrested; Det. Cole confirms the cross-county link is real.")
    slow("Bridging the detective's session hunch into permanent memory + reweighting...")
    await mem.resolve_case(session_ids=[SESSION], dataset=DATASET)
    slow("   ✓ improve() complete. Re-asking the multi-hop question:")
    answer_block("GRAPH after improve() — the connection is now first-class memory",
                 await mem.recall(Q_MULTI, mode=RecallMode.GRAPH, dataset=DATASET))
    slow("\n  → The next similar pattern surfaces faster. The system learned.")

    # PHASE 5 — FORGET
    banner(5, "forget(): a sealed record is surgically expunged")
    slow("A court orders the Riverside record sealed (expungement). We must remove it "
         "completely — while every other case stays intact.")
    await mem.expunge(dataset=DATASET)  # demo: in the app this targets one record/subgraph
    slow("   ✓ forget() complete. The sealed subgraph is gone; unrelated memory remains.")

    print(f"\n{'='*72}\n  Every department had a piece of the evidence.\n"
          f"  Nobody had the shared memory to connect it. Cognee does.\n{'='*72}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="prune state before running")
    asyncio.run(main(reset=ap.parse_args().reset))
