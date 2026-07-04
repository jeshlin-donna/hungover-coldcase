#!/usr/bin/env python3
"""Create a consistent ColdCache domain DB + evidence backup."""
from __future__ import annotations
import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "backups")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = args.output / f"coldcache-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    source_db = ROOT / "data" / "coldcache.db"
    if source_db.exists():
        with sqlite3.connect(source_db) as source, sqlite3.connect(target / "coldcache.db") as destination:
            source.backup(destination)
    cases = ROOT / "data" / "cases"
    if cases.exists(): shutil.copytree(cases, target / "cases")
    print(target)

if __name__ == "__main__": main()
