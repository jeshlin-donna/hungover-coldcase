"""Durable ColdCache case, evidence, and job state (application-owned SQLite)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("COLDCACHE_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
DB_PATH = DATA_DIR / "coldcache.db"
CASE_FILES = DATA_DIR / "cases"


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30, factory=ClosingConnection)
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
        CREATE TABLE IF NOT EXISTS job_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
          job_id TEXT NOT NULL, event_type TEXT NOT NULL, payload TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS case_analyses (
          case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
          graph_revision INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)
        columns = {row[1] for row in con.execute("PRAGMA table_info(jobs)")}
        for name, definition in {
            "lease_owner": "TEXT", "lease_expires_at": "TEXT", "heartbeat_at": "TEXT",
            "idempotency_key": "TEXT"
        }.items():
            if name not in columns: con.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_job ON jobs(evidence_id,kind) WHERE status IN ('queued','running')")
        con.execute("INSERT OR IGNORE INTO schema_migrations VALUES (1,?)", (now(),))
        # Only abandoned leases recover; a second healthy process must not steal work.
        stamp = now()
        con.execute("""UPDATE jobs SET status='queued',stage='recovering',progress=0,
          lease_owner=NULL,lease_expires_at=NULL,updated_at=?
          WHERE status='running' AND (lease_expires_at IS NULL OR lease_expires_at < ?)""", (stamp, stamp))


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


def archive_case(case_id: str, archived: bool) -> dict | None:
    return update_case(case_id, {"status": "archived" if archived else "open"})


def save_evidence(case_id: str, filename: str, content: bytes, media_type: str | None,
                  modality: str, context: str = "") -> tuple[dict, dict]:
    digest = hashlib.sha256(content).hexdigest()
    temp_dir = DATA_DIR / "upload_tmp"; temp_dir.mkdir(parents=True, exist_ok=True)
    temp = temp_dir / str(uuid.uuid4()); temp.write_bytes(content)
    return save_evidence_file(case_id, filename, temp, len(content), digest, media_type, modality, context)


def save_evidence_file(case_id: str, filename: str, temp: Path, size_bytes: int, digest: str,
                       media_type: str | None, modality: str, context: str = "") -> tuple[dict, dict | None]:
    evidence_id = str(uuid.uuid4()); stamp = now()
    with connect() as con:
        duplicate = con.execute("SELECT * FROM evidence_items WHERE case_id=? AND sha256=? AND status!='deleted'", (case_id, digest)).fetchone()
    if duplicate:
        temp.unlink(missing_ok=True)
        item = dict(duplicate); item["duplicate_of"] = {"id": item["id"], "original_filename": item["original_filename"], "status": item["status"]}
        return item, None
    suffix = Path(filename).suffix.lower()[:12]
    relative = Path("cases") / case_id / "originals" / f"{evidence_id}{suffix}"
    target = DATA_DIR / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target_temp = target.with_suffix(target.suffix + ".tmp")
    temp.replace(target_temp); target_temp.replace(target)
    with connect() as con:
        con.execute("""INSERT INTO evidence_items
          (id,case_id,original_filename,media_type,modality,size_bytes,sha256,storage_key,context,status,created_at,updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,'queued_analysis',?,?)""",
          (evidence_id, case_id, filename, media_type, modality, size_bytes, digest, str(relative), context, stamp, stamp))
        job_id = str(uuid.uuid4())
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,'analyze','queued','queued',0,?,?)",
                    (job_id, case_id, evidence_id, stamp, stamp))
        con.execute("UPDATE cases SET last_activity_at=?,updated_at=? WHERE id=?", (stamp, stamp, case_id))
    item = get_evidence(evidence_id); item["duplicate_of"] = None
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


def _event(con, job_id: str, case_id: str, event_type: str, payload: dict) -> None:
    con.execute("INSERT INTO job_events(case_id,job_id,event_type,payload,created_at) VALUES (?,?,?,?,?)",
                (case_id, job_id, event_type, json.dumps(payload), now()))


def claim_job(worker_id: str = "worker") -> dict | None:
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM jobs WHERE status='queued' AND cancel_requested=0 ORDER BY created_at LIMIT 1").fetchone()
        if not row: return None
        stamp = now()
        lease = (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat()
        con.execute("UPDATE jobs SET status='running',stage='starting',progress=2,attempt=attempt+1,started_at=COALESCE(started_at,?),updated_at=?,lease_owner=?,lease_expires_at=?,heartbeat_at=? WHERE id=? AND status='queued'", (stamp, stamp, worker_id, lease, stamp, row["id"]))
        evidence_status = "analyzing" if row["kind"] == "analyze" else "ingesting"
        con.execute("UPDATE evidence_items SET status=?,updated_at=? WHERE id=?", (evidence_status, stamp, row["evidence_id"]))
        _event(con, row["id"], row["case_id"], "job.started", {"stage": "starting", "progress": 2})
    return get_job(row["id"])


def recover_expired_jobs() -> int:
    stamp = now()
    with connect() as con:
        rows = con.execute("SELECT id,case_id FROM jobs WHERE status='running' AND (lease_expires_at IS NULL OR lease_expires_at < ?)", (stamp,)).fetchall()
        for row in rows:
            con.execute("UPDATE jobs SET status='queued',stage='recovering',progress=0,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=?", (stamp, row["id"]))
            _event(con, row["id"], row["case_id"], "job.recovered", {})
        return len(rows)


def heartbeat(job_id: str) -> None:
    stamp = now(); lease = (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat()
    with connect() as con:
        con.execute("UPDATE jobs SET heartbeat_at=?,lease_expires_at=?,updated_at=? WHERE id=? AND status='running'", (stamp, lease, stamp, job_id))


def job_progress(job_id: str, stage: str, progress: int) -> None:
    with connect() as con:
        stamp = now(); lease = (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat()
        row = con.execute("SELECT case_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        con.execute("UPDATE jobs SET stage=?,progress=?,updated_at=?,heartbeat_at=?,lease_expires_at=? WHERE id=?", (stage, progress, stamp, stamp, lease, job_id))
        if row: _event(con, job_id, row["case_id"], "job.progress", {"stage": stage, "progress": progress})


def is_cancel_requested(job_id: str) -> bool:
    with connect() as con:
        row = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
        return bool(row and row[0])


def finish_cancelled(job: dict) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET status='cancelled',updated_at=? WHERE id=?", (stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='cancelled',stage='cancelled',finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))
        _event(con, job["id"], job["case_id"], "job.cancelled", {})


def finish_analysis(job: dict, output: str) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET model_output=?,reviewed_text=?,status='awaiting_review',error_message=NULL,updated_at=? WHERE id=?", (output, output, stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='succeeded',stage='awaiting_review',progress=100,finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))
        _event(con, job["id"], job["case_id"], "job.succeeded", {"stage": "awaiting_review"})


def queue_ingestion(case_id: str, evidence_id: str, reviewed_text: str, context: str) -> dict:
    stamp = now(); job_id = str(uuid.uuid4())
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        current = con.execute("SELECT model_output,status FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not current: raise KeyError("Evidence not found")
        if current["status"] != "awaiting_review": raise ValueError(f"Evidence cannot be confirmed from {current['status']}")
        rev = con.execute("SELECT COUNT(*) FROM evidence_revisions WHERE evidence_id=?", (evidence_id,)).fetchone()[0] + 1
        con.execute("INSERT INTO evidence_revisions VALUES (?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), evidence_id, rev, current["model_output"] or "", reviewed_text, context, stamp, stamp))
        con.execute("UPDATE evidence_items SET reviewed_text=?,context=?,status='queued_ingestion',updated_at=? WHERE id=?", (reviewed_text, context, stamp, evidence_id))
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,'ingest','queued','queued',0,?,?)", (job_id, case_id, evidence_id, stamp, stamp))
        _event(con, job_id, case_id, "job.queued", {"kind": "ingest"})
    return get_job(job_id)


def queue_reindex(case_id: str) -> dict:
    stamp = now(); job_id = str(uuid.uuid4())
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
            raise KeyError("Case not found")
        active = con.execute(
            "SELECT id FROM jobs WHERE case_id=? AND status IN ('queued','running') ORDER BY created_at LIMIT 1",
            (case_id,),
        ).fetchone()
        if active: raise ValueError("Case already has active work")
        con.execute(
            "INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) "
            "VALUES (?,?,NULL,'reindex','queued','queued',0,?,?)",
            (job_id, case_id, stamp, stamp),
        )
        _event(con, job_id, case_id, "job.queued", {"kind": "reindex"})
    return get_job(job_id)


def finish_ingestion(job: dict) -> None:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE evidence_items SET status='ingested',error_message=NULL,updated_at=? WHERE id=?", (stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='succeeded',stage='indexed',progress=100,finished_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["id"]))
        con.execute("UPDATE cases SET graph_revision=graph_revision+1,last_activity_at=?,updated_at=? WHERE id=?", (stamp, stamp, job["case_id"]))
        _event(con, job["id"], job["case_id"], "job.succeeded", {"stage": "indexed"})


def finish_reindex(job: dict, dataset_name: str) -> dict:
    """Activate a fully cognified replacement and finish its durable job atomically."""
    stamp = now()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        changed = con.execute(
            "UPDATE cases SET dataset_name=?,graph_revision=graph_revision+1,updated_at=?,last_activity_at=? WHERE id=?",
            (dataset_name, stamp, stamp, job["case_id"]),
        ).rowcount
        if not changed: raise KeyError("Case not found")
        con.execute("DELETE FROM case_analyses WHERE case_id=?", (job["case_id"],))
        con.execute(
            "UPDATE jobs SET status='succeeded',stage='indexed',progress=100,finished_at=?,updated_at=? WHERE id=?",
            (stamp, stamp, job["id"]),
        )
        _event(con, job["id"], job["case_id"], "job.succeeded", {"stage": "indexed"})
    return get_case(job["case_id"])


def fail_job(job: dict, message: str) -> None:
    stamp = now(); status = "analysis_failed" if job["kind"] == "analyze" else "ingestion_failed"
    with connect() as con:
        con.execute("UPDATE evidence_items SET status=?,error_message=?,updated_at=? WHERE id=?", (status, message[:1000], stamp, job["evidence_id"]))
        con.execute("UPDATE jobs SET status='failed',stage='failed',error_message=?,finished_at=?,updated_at=? WHERE id=?", (message[:1000], stamp, stamp, job["id"]))
        _event(con, job["id"], job["case_id"], "job.failed", {"error": message[:1000]})


def retry_evidence(case_id: str, evidence_id: str, kind: str) -> dict:
    stamp = now(); job_id = str(uuid.uuid4())
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        item = con.execute("SELECT id,status FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not item: raise KeyError("Evidence not found")
        expected = "analysis_failed" if kind == "analyze" else "ingestion_failed"
        if item["status"] != expected: raise ValueError(f"Retry is only allowed from {expected}")
        con.execute("UPDATE evidence_items SET status=?,error_message=NULL,updated_at=? WHERE id=?", (f"queued_{'analysis' if kind == 'analyze' else 'ingestion'}", stamp, evidence_id))
        con.execute("INSERT INTO jobs (id,case_id,evidence_id,kind,status,stage,progress,created_at,updated_at) VALUES (?,?,?,?,'queued','queued',0,?,?)", (job_id, case_id, evidence_id, kind, stamp, stamp))
    return get_job(job_id)


def cancel_job(case_id: str, evidence_id: str) -> bool:
    stamp = now()
    with connect() as con:
        active = con.execute("SELECT * FROM jobs WHERE case_id=? AND evidence_id=? AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1", (case_id, evidence_id)).fetchone()
        if not active: return False
        if active["kind"] == "ingest" and active["status"] == "running": return False
        con.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,updated_at=? WHERE id=?", (stamp, active["id"]))
        con.execute("UPDATE evidence_items SET status='cancelled',updated_at=? WHERE id=? AND case_id=?", (stamp, evidence_id, case_id))
        _event(con, active["id"], case_id, "job.cancel_requested", {})
        return True


def save_review_draft(case_id: str, evidence_id: str, reviewed_text: str, context: str,
                      expected_updated_at: str | None = None) -> dict:
    with connect() as con:
        row = con.execute("SELECT status FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not row: raise KeyError("Evidence not found")
        if row["status"] != "awaiting_review": raise ValueError("Draft is editable only while awaiting review")
        stamp = now()
        if expected_updated_at:
            changed = con.execute("UPDATE evidence_items SET reviewed_text=?,context=?,updated_at=? WHERE id=? AND updated_at=?",
                                  (reviewed_text, context, stamp, evidence_id, expected_updated_at)).rowcount
            if not changed: raise ValueError("Review changed in another tab; refresh before editing.")
        else:
            con.execute("UPDATE evidence_items SET reviewed_text=?,context=?,updated_at=? WHERE id=?", (reviewed_text, context, stamp, evidence_id))
    return get_evidence(evidence_id)


def list_events(case_id: str, after_id: int = 0) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM job_events WHERE case_id=? AND id>? ORDER BY id LIMIT 200", (case_id, after_id)).fetchall()
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]


def get_analysis(case_id: str, graph_revision: int) -> dict | None:
    with connect() as con:
        row = con.execute("SELECT payload FROM case_analyses WHERE case_id=? AND graph_revision=?", (case_id, graph_revision)).fetchone()
    return json.loads(row["payload"]) if row else None


def save_analysis(case_id: str, graph_revision: int, payload: dict) -> None:
    with connect() as con:
        con.execute("INSERT INTO case_analyses(case_id,graph_revision,payload,updated_at) VALUES (?,?,?,?) ON CONFLICT(case_id) DO UPDATE SET graph_revision=excluded.graph_revision,payload=excluded.payload,updated_at=excluded.updated_at",
                    (case_id, graph_revision, json.dumps(payload), now()))


def bump_graph_revision(case_id: str) -> dict:
    stamp = now()
    with connect() as con:
        con.execute("UPDATE cases SET graph_revision=graph_revision+1,updated_at=?,last_activity_at=? WHERE id=?", (stamp, stamp, case_id))
        con.execute("DELETE FROM case_analyses WHERE case_id=?", (case_id,))
    return get_case(case_id)


def activate_reindexed_dataset(case_id: str, dataset_name: str) -> dict:
    """Atomically point a case at a fully-built replacement Cognee dataset."""
    stamp = now()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        changed = con.execute(
            "UPDATE cases SET dataset_name=?,graph_revision=graph_revision+1,updated_at=?,last_activity_at=? WHERE id=?",
            (dataset_name, stamp, stamp, case_id),
        ).rowcount
        if not changed: raise KeyError("Case not found")
        con.execute("DELETE FROM case_analyses WHERE case_id=?", (case_id,))
    return get_case(case_id)


def delete_evidence(case_id: str, evidence_id: str, allow_ingested: bool = False) -> bool:
    with connect() as con:
        row = con.execute("SELECT * FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not row: return False
        if row["status"] == "ingested" and not allow_ingested: raise ValueError("Ingested evidence requires a case graph rebuild")
        if con.execute("SELECT 1 FROM jobs WHERE evidence_id=? AND status IN ('queued','running')", (evidence_id,)).fetchone(): raise ValueError("Evidence has active work")
        con.execute("DELETE FROM evidence_items WHERE id=?", (evidence_id,))
        if row["status"] == "ingested": con.execute("UPDATE cases SET graph_revision=graph_revision+1,updated_at=?,last_activity_at=? WHERE id=?", (now(), now(), case_id))
    path = storage_path(dict(row)); path.unlink(missing_ok=True)
    return True


def delete_case_records(case_id: str) -> bool:
    with connect() as con:
        if con.execute("SELECT 1 FROM jobs WHERE case_id=? AND status IN ('queued','running')", (case_id,)).fetchone(): raise ValueError("Case has active work")
        found = con.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone()
        if not found: return False
        con.execute("DELETE FROM cases WHERE id=?", (case_id,))
    shutil.rmtree(CASE_FILES / case_id, ignore_errors=True)
    return True


def storage_path(item: dict) -> Path:
    return DATA_DIR / item["storage_key"]
