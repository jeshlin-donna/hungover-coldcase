import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from backend import case_store


class CasePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch.object(case_store, "ROOT", root), patch.object(case_store, "DB_PATH", root / "db.sqlite")]
        for item in self.patches: item.start()
        case_store.init_db()
        self.case = case_store.create_case({"title": "Test case"})

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def analyzed(self):
        item, job = case_store.save_evidence(self.case["id"], "evidence.txt", b"fact", "text/plain", "text", "")
        case_store.finish_analysis(job, "model output")
        return case_store.get_evidence(item["id"])

    def test_duplicate_is_skipped(self):
        first, _ = case_store.save_evidence(self.case["id"], "one.txt", b"same", None, "text", "")
        second, job = case_store.save_evidence(self.case["id"], "two.txt", b"same", None, "text", "")
        self.assertIsNone(job)
        self.assertEqual(first["id"], second["id"])

    def test_confirmation_is_idempotent(self):
        item = self.analyzed()
        case_store.queue_ingestion(self.case["id"], item["id"], "verified", "")
        with self.assertRaises(ValueError):
            case_store.queue_ingestion(self.case["id"], item["id"], "verified again", "")

    def test_stale_review_draft_is_rejected(self):
        item = self.analyzed()
        case_store.save_review_draft(self.case["id"], item["id"], "first", "", item["updated_at"])
        with self.assertRaises(ValueError):
            case_store.save_review_draft(self.case["id"], item["id"], "stale", "", item["updated_at"])

    def test_running_ingestion_cannot_be_cancelled(self):
        item = self.analyzed()
        job = case_store.queue_ingestion(self.case["id"], item["id"], "verified", "")
        claimed = case_store.claim_job("test-worker")
        self.assertEqual(job["id"], claimed["id"])
        self.assertFalse(case_store.cancel_job(self.case["id"], item["id"]))

    def test_expired_lease_recovers(self):
        item, job = case_store.save_evidence(self.case["id"], "lease.txt", b"x", None, "text", "")
        case_store.claim_job("dead-worker")
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        with case_store.connect() as con:
            con.execute("UPDATE jobs SET lease_expires_at=? WHERE id=?", (expired, job["id"]))
        self.assertEqual(1, case_store.recover_expired_jobs())
        self.assertEqual("queued", case_store.get_job(job["id"])["status"])

    def test_cross_case_confirmation_is_blocked(self):
        other = case_store.create_case({"title": "Other"})
        item = self.analyzed()
        with self.assertRaises(KeyError):
            case_store.queue_ingestion(other["id"], item["id"], "wrong case", "")


if __name__ == "__main__":
    unittest.main()
