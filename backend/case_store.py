"""Durable ColdCache case, evidence, and job state (application-owned SQLite)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "coldcache.db"
CASE_FILES = ROOT / "data" / "cases"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, reference_number TEXT,
          description TEXT, jurisdiction TEXT, incident_date TEXT,
          status TEXT NOT NULL DEFAULT 'open', dataset_name TEXT NOT NULL UNIQUE,
          graph_revision INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_activity_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evidence_items (
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          original_filename TEXT NOT NULL, media_type TEXT, modality TEXT NOT NULL,
          size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, storage_key TEXT NOT NULL,
          context TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
          model_output TEXT, reviewed_text TEXT, error_message TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS evidence_case_idx ON evidence_items(case_id, created_at);
        CREATE INDEX IF NOT EXISTS evidence_hash_idx ON evidence_items(case_id, sha256);
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          evidence_id TEXT REFERENCES evidence_items(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL,
          progress INTEGER NOT NULL DEFAULT 0, attempt INTEGER NOT NULL DEFAULT 0,
          error_message TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs(status, created_at);
        CREATE INDEX IF NOT EXISTS jobs_case_idx ON jobs(case_id, updated_at);
        CREATE TABLE IF NOT EXISTS evidence_revisions (
          id TEXT PRIMARY KEY, evidence_id TEXT NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
          revision_number INTEGER NOT NULL, model_output TEXT NOT NULL,
          reviewed_text TEXT NOT NULL, context_snapshot TEXT NOT NULL,
          created_at TEXT NOT NULL, confirmed_at TEXT NOT NULL,
          UNIQUE(evidence_id, revision_number)
        );
        """)
        # A crashed process must not leave work permanently running.
        con.execute("UPDATE jobs SET status='queued', stage='recovering', progress=0, updated_at=? WHERE status='running'", (now(),))


def row_dict(row):
    return dict(row) if row else None


def create_case(payload: dict) -> dict:
    case_id = str(uuid.uuid4())
    stamp = now()
    dataset = f"case_{case_id.replace('-', '')}"
    with connect() as con:
        con.execute("""INSERT INTO cases
          (id,title,reference_number,description,jurisdiction,incident_date,status,dataset_name,created_at,updated_at,last_activity_at)
          VALUES (?,?,?,?,?,?,'open',?,?,?,?)""",
          (case_id, payload["title"].strip(), payload.get("reference_number"), payload.get("description"),
           payload.get("jurisdiction"), payload.get("incident_date"), dataset, stamp, stamp, stamp))
    return get_case(case_id)


def list_cases() -> list[dict]:
    with connect() as con:
        rows = con.execute("""SELECT c.*,
          (SELECT COUNT(*) FROM evidence_items e WHERE e.case_id=c.id) evidence_count,
          (SELECT COUNT(*) FROM jobs j WHERE j.case_id=c.id AND j.status IN ('queued','running')) active_jobs,
          (SELECT COUNT(*) FROM jobs j WHERE j.case_id=c.id AND j.status='failed') failed_jobs
          FROM cases c ORDER BY c.last_activity_at DESC""").fetchall()
    return [dict(r) for r in rows]


def get_case(case_id: str) -> dict | None:
    with connect() as con:
        return row_dict(con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())


def update_case(case_id: str, payload: dict) -> dict | None:
    allowed = ["title", "reference_number", "description", "jurisdiction", "incident_date", "status"]
    fields = [(key, payload[key]) for key in allowed if key in payload]
    if not fields: return get_case(case_id)
    stamp = now(); sql = ",".join(f"{key}=?" for key, _ in fields)
    with connect() as con:
        con.execute(f"UPDATE cases SET {sql}, updated_at=?, last_activity_at=? WHERE id=?",
                    tuple(value for _, value in fields) + (stamp, stamp, case_id))
    return get_case(case_id)


def save_evidence(case_id: str, filename: str, content: bytes, media_type: str | None,
                  modality: str, context: str = "") -> tuple[dict, dict]:
    evidence_id = str(uuid.uuid4()); stamp = now()
    digest = hashlib.sha256(content).hexdigest()
    suffix = Path(filename).suffix.lower()[:12]
    relative = Path("cases") / case_id / "originals" / f"{evidence_id}{suffix}"
    target = ROOT / "data" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_bytes(content); temp.replace(target)
    with connect() as con:
        duplicate = con.execute("SELECT id,original_filename,status FROM evidence_items WHERE case_id=? AND sha256=?", (case_id, digest)).fetchone()
        con.execute("""INSERT INTO evidence_items
          (id,case_id,original_filename,media_type,modality,size_bytes,sha256,storage_key,context,status,created_at,updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,'queued_analysis',?,?)""",
          (evidence_id, case_id, filename, media_type, modality, len(content), digest, str(relative), context, stamp, stamp))
        job_id = str(uuid.uuid4())
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,'analyze','queued','queued',0,?,?)",
                    (job_id, case_id, evidence_id, stamp, stamp))
        con.execute("UPDATE cases SET last_activity_at=?,updated_at=? WHERE id=?", (stamp, stamp, case_id))
    item = get_evidence(evidence_id); item["duplicate_of"] = dict(duplicate) if duplicate else None
    return item, get_job(job_id)


def list_evidence(case_id: str) -> list[dict]:
    with connect() as con:
        rows = con.execute("""SELECT e.*,
          (SELECT id FROM jobs j WHERE j.evidence_id=e.id ORDER BY created_at DESC LIMIT 1) job_id
          FROM evidence_items e WHERE case_id=? ORDER BY created_at DESC""", (case_id,)).fetchall()
    return [dict(r) for r in rows]


def get_evidence(evidence_id: str) -> dict | None:
    with connect() as con:
        return row_dict(con.execute("SELECT * FROM evidence_items WHERE id=?", (evidence_id,)).fetchone())


def get_job(job_id: str) -> dict | None:
    with connect() as con:
        return row_dict(con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())


def list_jobs(case_id: str) -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM jobs WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()]


def claim_job() -> dict | None:
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM jobs WHERE status='queued' AND cancel_requested=0 ORDER BY created_at LIMIT 1").fetchone()
        if not row: return None
        stamp = now()
        con.execute("UPDATE jobs SET status='running',stage='starting',progress=2,attempt=attempt+1,started_at=COALESCE(started_at,?),updated_at=? WHERE id=? AND status='queued'", (stamp, stamp, row["id"]))
        evidence_status = "analyzing" if row["kind"] == "analyze" else "ingesting"
        con.execute("UPDATE evidence_items SET status=?,updated_at=? WHERE id=?", (evidence_status, stamp, row["evidence_id"]))
    return get_job(row["id"])


def job_progress(job_id: str, stage: str, progress: int) -> None:
    with connect() as con:
        con.execute("UPDATE jobs SET stage=?,progress=?,updated_at=? WHERE id=?", (stage, progress, now(), job_id))


def is_cancel_requested(job_id: str) -> bool:
    with connect() as con:
        row = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
        return bool(row and row[0])


def finish_cancelled(job: dict) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET status='cancelled',updated_at=? WHERE id=?", (stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='cancelled',stage='cancelled',finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))


def finish_analysis(job: dict, output: str) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET model_output=?,reviewed_text=?,status='awaiting_review',error_message=NULL,updated_at=? WHERE id=?", (output, output, stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='succeeded',stage='awaiting_review',progress=100,finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))


def queue_ingestion(case_id: str, evidence_id: str, reviewed_text: str, context: str) -> dict:
    stamp = now(); job_id = str(uuid.uuid4())
    with connect() as con:
        current = con.execute("SELECT model_output FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not current: raise KeyError("Evidence not found")
        rev = con.execute("SELECT COUNT(*) FROM evidence_revisions WHERE evidence_id=?", (evidence_id,)).fetchone()[0] + 1
        con.execute("INSERT INTO evidence_revisions VALUES (?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), evidence_id, rev, current["model_output"] or "", reviewed_text, context, stamp, stamp))
        con.execute("UPDATE evidence_items SET reviewed_text=?,context=?,status='queued_ingestion',updated_at=? WHERE id=?", (reviewed_text, context, stamp, evidence_id))
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,'ingest','queued','queued',0,?,?)", (job_id, case_id, evidence_id, stamp, stamp))
    return get_job(job_id)


def finish_ingestion(job: dict) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET status='ingested',error_message=NULL,updated_at=? WHERE id=?", (stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='succeeded',stage='indexed',progress=100,finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))
        con.execute("UPDATE cases SET graph_revision=graph_revision+1,last_activity_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["case_id"]))


def fail_job(job: dict, message: str) -> None:
    stamp = now(); status = "analysis_failed" if job["kind"] == "analyze" else "ingestion_failed"
    with connect() as con:
        con.execute("UPDATE evidence_items SET status=?,error_message=?,updated_at=? WHERE id=?", (status, message[:1000], stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='failed',stage='failed',error_message=?,finished_at=?,updated_at=? WHERE id=?", (message[:1000], stamp, stamp, job["id"]))


def retry_evidence(case_id: str, evidence_id: str, kind: str) -> dict:
    stamp = now(); job_id = str(uuid.uuid4())
    with connect() as con:
        item = con.execute("SELECT id FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not item: raise KeyError("Evidence not found")
        con.execute("UPDATE evidence_items SET status=?,error_message=NULL,updated_at=? WHERE id=?", (f"queued_{'analysis' if kind == 'analyze' else 'ingestion'}", stamp, evidence_id))
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,?,'queued','queued',0,?,?)", (job_id, case_id, evidence_id, kind, stamp, stamp))
    return get_job(job_id)


def cancel_job(case_id: str, evidence_id: str) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,updated_at=? WHERE case_id=? AND evidence_id=? AND status IN ('queued','running')", (stamp, case_id, evidence_id))
        con.execute("UPDATE evidence_items SET status='cancelled',updated_at=? WHERE id=? AND case_id=?", (stamp, evidence_id, case_id))


def storage_path(item: dict) -> Path:
    return ROOT / "data" / item["storage_key"]
