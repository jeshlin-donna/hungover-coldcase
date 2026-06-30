"""
Priority 0 smoke test — RUN THIS FIRST, on a machine that can pip install cognee.

    pip install -r requirements.txt
    cp .env.example .env        # add your LLM_API_KEY
    python backend/smoke_test.py

Its only job: exercise all 4 Cognee APIs against the LIVE SDK and PRINT the real
return shapes, so we can pin the  # VERIFY  spots in memory_service.py and fill in
docs/API_NOTES.md. Do NOT build anything else until this passes.
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
assert os.getenv("LLM_API_KEY"), "Set LLM_API_KEY in .env first."

import memory_service as mem  # noqa: E402


def show(label, obj):
    print(f"\n--- {label} ---")
    print("type:", type(obj))
    print("repr:", repr(obj)[:800])
    if isinstance(obj, (list, tuple)) and obj:
        print("elem[0] type:", type(obj[0]))
        print("elem[0] attrs:", [a for a in dir(obj[0]) if not a.startswith("_")][:25])


async def main():
    print("SearchType imported as:", mem.SearchType)

    print("\n[1/5] remember()")
    await mem.remember(
        "On March 3, a burglary at 14 Maple Heights used a flat-head pry tool "
        "(8mm) and a dark blue sedan was seen leaving. Detective: A. Cole.",
        dataset="smoketest",
    )
    print("remember + cognify + indexing OK")

    print("\n[2/5] recall() in all 3 modes")
    for mode in (mem.RecallMode.GRAPH, mem.RecallMode.VECTOR, mem.RecallMode.INSIGHTS):
        try:
            r = await mem.recall("What tool was used in the Maple Heights burglary?",
                                  mode=mode, dataset="smoketest")
            show(f"recall:{mode.value}", r.raw)
        except Exception as e:
            print(f"recall:{mode.value} FAILED -> {type(e).__name__}: {e}")

    print("\n[3/5] log_hunch() -> session memory")
    try:
        await mem.log_hunch("Hunch: same pry tool as the Riverside job?",
                            session_id="case-001", dataset="smoketest")
        print("log_hunch OK")
    except Exception as e:
        print(f"log_hunch FAILED -> {type(e).__name__}: {e}")

    print("\n[4/5] resolve_case() -> improve(session_ids=...)")
    try:
        await mem.resolve_case(session_ids=["case-001"], dataset="smoketest")
        print("resolve_case/improve OK")
    except Exception as e:
        print(f"resolve_case FAILED -> {type(e).__name__}: {e}")

    print("\n[5/5] expunge() -> forget(dataset=...)")
    try:
        await mem.expunge("smoketest")
        print("expunge/forget OK")
    except Exception as e:
        print(f"expunge FAILED -> {type(e).__name__}: {e}")

    print("\nDONE. Copy the real types/shapes above into docs/API_NOTES.md and "
          "fix any # VERIFY in memory_service.py.")


if __name__ == "__main__":
    asyncio.run(main())
