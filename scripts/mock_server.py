"""
Zero-dependency mock backend for the frontend. No pip needed — pure stdlib, runs anywhere.

    python scripts/mock_server.py            # serves http://localhost:8010

Implements the API_CONTRACT.md shapes from frontend/mock/*.json plus synthesized
/recall, /hunch, /resolve, /expunge so Benjy can build the full UX before the real
Cognee backend exists. Sam's FastAPI later mirrors these exact routes.
"""
import json
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

MOCK = Path(__file__).resolve().parents[1] / "frontend" / "mock"
BENCH = Path(__file__).resolve().parents[1] / "benchmark" / "results.json"
PENDING = {}


def load(name):
    return json.loads((MOCK / name).read_text())


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass  # quiet

    def do_OPTIONS(self):
        self._send({})

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        if path == "/graph":
            return self._send(load("graph.json"))
        if path == "/graph/temporal":
            time = qs.get("time", [None])[0]
            full = load("graph.json")
            if not time:
                return self._send(full)
            nodes = full.get("nodes", [])
            visible_ids = {n["id"] for n in nodes if not n.get("date") or n["date"] <= time}
            filtered_nodes = [n for n in nodes if n["id"] in visible_ids]
            filtered_edges = [
                e for e in full.get("edges", [])
                if e["source"] in visible_ids and e["target"] in visible_ids
            ]
            return self._send({
                "nodes": filtered_nodes,
                "edges": filtered_edges,
                "contradictions": full.get("contradictions", []),
                "time": time,
            })
        if path == "/contradictions":
            return self._send({"contradictions": load("graph.json").get("contradictions", [])})
        if path == "/timeline":
            return self._send(load("timeline.json"))
        if path == "/recall/compare":
            return self._send(load("recall_compare.json"))
        if path == "/benchmark":
            return self._send(json.loads(BENCH.read_text()) if BENCH.exists()
                              else {"note": "run benchmark.py to populate"})
        if path == "/health":
            return self._send({"ok": True, "mode": "degraded"})
        if path == "/stats":
            g = load("graph.json")
            return self._send({"nodes": len(g["nodes"]), "docs": 11,
                               "jurisdictions": len({n["id"] for n in g["nodes"] if n.get("type") == "jurisdiction"}),
                               "alibi_break": bool(g.get("contradictions")), "mode": "degraded"})
        if path == "/chat/suggestions":
            return self._send({"suggestions": [
                "What evidence connects incidents across jurisdictions?",
                "Which claims are contradicted by verified records?",
                "What important gap should an investigator pursue next?",
            ], "mode": "degraded"})
        return self._send({"error": "not found", "path": path}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        if path == "/ingest-files/analyze":
            text = raw.decode("utf-8", errors="ignore")
            filenames = re.findall(r'filename="([^"]+)"', text)
            results = []
            for index, filename in enumerate(filenames):
                review_id = secrets.token_urlsafe(12)
                extracted = ("MODEL-GENERATED / EXTRACTED CONTENT — REVIEW BEFORE INGESTION\n"
                             f"{filename}\n\nAnalysis preview unavailable in degraded mode. Add verified observations before confirming.")
                PENDING[review_id] = {"filename": filename, "text": extracted}
                results.append({"ok": True, "index": index, "review_id": review_id,
                                "filename": filename, "type": "evidence",
                                "extracted_text": extracted, "requires_confirmation": True})
            return self._send({"ok": True, "results": results, "mode": "degraded"})
        if path == "/ingest-file/analyze":
            text = raw.decode("utf-8", errors="ignore")
            filename = (re.search(r'filename="([^"]+)"', text) or [None, "evidence"])[1]
            review_id = secrets.token_urlsafe(12)
            extracted = f"MODEL-GENERATED / EXTRACTED CONTENT — REVIEW BEFORE INGESTION\n{filename}\n\nAnalysis preview unavailable in degraded mode. Add verified observations before confirming."
            PENDING[review_id] = {"filename": filename, "text": extracted}
            return self._send({"ok": True, "review_id": review_id, "filename": filename,
                               "type": "evidence", "extracted_text": extracted,
                               "requires_confirmation": True, "mode": "degraded"})
        if path == "/ingest-file":
            text = raw.decode("utf-8", errors="ignore")
            filename = (re.search(r'filename="([^"]+)"', text) or [None, "note.txt"])[1]
            return self._send({"ok": True, "filename": filename, "type": "text",
                               "graph_node_id": "evidence:mock-text", "verified": True,
                               "mode": "degraded"})
        body = json.loads(raw or b"{}")
        if path == "/ingest-files/confirm":
            results = []
            for index, item in enumerate(body.get("items", [])):
                pending = PENDING.pop(item.get("review_id", ""), None)
                if pending:
                    results.append({"ok": True, "index": index, "filename": pending["filename"],
                                    "type": "evidence", "graph_node_id": f"evidence:mock-{index + 1}",
                                    "verified": True, "mode": "degraded"})
                else:
                    results.append({"ok": False, "index": index, "error": "Review not found."})
            return self._send({"ok": all(item["ok"] for item in results),
                               "results": results, "mode": "degraded"})
        if path == "/ingest-file/confirm":
            pending = PENDING.pop(body.get("review_id", ""), None)
            if not pending:
                return self._send({"detail": "Review not found or already confirmed."}, 404)
            return self._send({"ok": True, "filename": pending["filename"], "type": "evidence",
                               "graph_node_id": f"evidence:mock-{len(PENDING) + 1}",
                               "verified": True, "mode": "degraded"})
        if path == "/chat":
            return self._send({"answer": "Case chat is in degraded mode. Start the live backend to query the configured LLM and Cognee graph.",
                               "sources": [], "mode": "degraded"})
        if path == "/recall":
            cmp = load("recall_compare.json")["results"]
            mode = body.get("mode", "graph")
            key = {"graph": "cognee_graph", "vector": "cognee_vector",
                   "insights": "cognee_graph"}.get(mode, "cognee_graph")
            r = cmp[key]
            return self._send({"mode": mode, **r})
        if path == "/hunch":
            return self._send({"ok": True, "session_id": body.get("session_id")})
        if path == "/resolve":
            return self._send({"ok": True, "metric": "recall@3 on multi-hop",
                               "before": 0.42, "after": 0.71})
        if path == "/expunge":
            ds = body.get("dataset", "case:RV-0788")
            g = load("graph.json")
            removed = [n["id"] for n in g["nodes"]
                       if ds.split(":")[-1] in n["id"]]
            g["nodes"] = [n for n in g["nodes"] if n["id"] not in removed]
            g["edges"] = [e for e in g["edges"]
                          if e["source"] not in removed and e["target"] not in removed]
            return self._send({"ok": True, "removed": removed, "graph": g})
        return self._send({"error": "not found", "path": path}, 404)


if __name__ == "__main__":
    print("mock backend → http://localhost:8010  (GET /graph /timeline /recall/compare "
          "/benchmark · POST /recall /hunch /resolve /expunge)")
    ThreadingHTTPServer(("0.0.0.0", 8010), Handler).serve_forever()
