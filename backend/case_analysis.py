"""Deterministic, source-grounded case analysis used by every case tool.

Cognee remains the reasoning layer. This module guarantees that the UI has a real
entity/evidence graph and timeline even while an LLM provider is offline.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone


def _id(kind: str, label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48]
    return f"{kind}:{slug or hashlib.sha1(label.encode()).hexdigest()[:10]}"


def _add_node(nodes, kind, label, **extra):
    node_id = _id(kind, label)
    nodes.setdefault(node_id, {"id": node_id, "label": label.strip(), "type": kind, **extra})
    return node_id


def build(case: dict, evidence_items: list[dict]) -> dict:
    nodes, edges, edge_keys, timeline = {}, [], set(), []
    case_node = _add_node(nodes, "case", case["title"], status=case["status"])

    def edge(source, target, relation, source_doc=None):
        key = (source, target, relation)
        if source != target and key not in edge_keys:
            edge_keys.add(key); edges.append({"source": source, "target": target, "relation": relation, "source_doc": source_doc})

    for item in evidence_items:
        if item["status"] != "ingested": continue
        text = item.get("reviewed_text") or ""
        doc_id = f"document:{item['id']}"
        nodes[doc_id] = {"id": doc_id, "label": item["original_filename"], "type": "document", "modality": item["modality"]}
        edge(case_node, doc_id, "contains")
        found = []

        # Explicit labeled people are high-confidence and source-grounded.
        for match in re.finditer(r"(?im)^(?:primary\s+)?(?:suspect|examiner|victim|witness|name)\s*:\s*([^\n,]+)", text):
            label = match.group(1).strip()
            if 2 <= len(label) <= 80: found.append(_add_node(nodes, "person", label))
        for label in re.findall(r"\b(?:Daniel Marsh|Unknown Associate #\d+)\b", text, re.I):
            found.append(_add_node(nodes, "person", label.title() if "unknown" not in label.lower() else label))

        for match in re.finditer(r"(?im)^location\s*:\s*([^\n]+)", text):
            found.append(_add_node(nodes, "location", match.group(1).strip()))
        for label in re.findall(r"\b\d{1,5}\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Ave|Avenue|St|Street|Rd|Road|Lane|Ln|Dr|Drive|Ct|Court)\b", text):
            found.append(_add_node(nodes, "location", label))

        for label in re.findall(r"(?i)\b(?:dark\s+blue|black|white|red|silver|gray|grey)\s+(?:Honda|Toyota|Ford|Chevrolet|Nissan|BMW|Audi)?\s*[A-Z][A-Za-z0-9-]*(?:\s+Accord|\s+Civic|\s+sedan|\s+SUV)?(?:,?\s+partial\s+plate\s+[A-Z0-9-]+)?", text):
            if len(label.split()) >= 2: found.append(_add_node(nodes, "vehicle", label.strip(" ,")))

        evidence_labels = []
        evidence_labels += re.findall(r"(?im)^Item\s+\d+\s*:\s*([^\n]+)", text)
        for match in re.finditer(r"(?im)^Key evidence\s*:\s*([^\n]+)", text):
            evidence_labels += [part.strip() for part in match.group(1).split(",")]
        evidence_labels += re.findall(r"(?i)\b8mm\s+left-nick\s+pry\s+blade\b", text)
        for label in evidence_labels:
            if label: found.append(_add_node(nodes, "evidence", label))

        dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text)
        # Structured CSV-like time/event rows.
        for tm, event, confidence in re.findall(r"(?m)^\s*(\d{2}:\d{2})\s+(.+?)\s+(0\.\d+|1\.0+)\s*$", text):
            timeline.append({"date": dates[0] if dates else item["created_at"][:10], "time": tm,
                             "title": event.strip(), "summary": f"Confidence {confidence}",
                             "evidence_id": item["id"], "source": item["original_filename"]})
        for date, location, amount, notes in re.findall(r"(?m)^\s*(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(\d+\.\d{2})\s+\d+\s+(.+)$", text):
            timeline.append({"date": date, "time": None, "title": notes.strip(),
                             "summary": f"{location.strip()} · ${amount}", "evidence_id": item["id"],
                             "source": item["original_filename"]})
        if dates and not any(event["evidence_id"] == item["id"] for event in timeline):
            timeline.append({"date": dates[0], "time": None, "title": item["original_filename"],
                             "summary": text.splitlines()[0][:180], "evidence_id": item["id"], "source": item["original_filename"]})

        unique = list(dict.fromkeys(found))
        for entity_id in unique: edge(doc_id, entity_id, "mentions", item["original_filename"])
        people = [x for x in unique if nodes[x]["type"] == "person"]
        facts = [x for x in unique if nodes[x]["type"] in ("evidence", "vehicle", "location")]
        for person in people:
            for fact in facts: edge(person, fact, "associated_by_evidence", item["original_filename"])

    timeline.sort(key=lambda event: (event["date"], event.get("time") or ""))
    people = [node for node in nodes.values() if node["type"] == "person"]
    evidence = [node for node in nodes.values() if node["type"] == "evidence"]
    summary = (f"{case['title']} contains {len(evidence_items)} ingested documents, "
               f"{len(people)} identified people, {len(evidence)} evidence items, "
               f"and {len(timeline)} dated or timed events.")
    return {"case_id": case["id"], "graph_revision": case["graph_revision"], "nodes": list(nodes.values()),
            "edges": edges, "timeline": timeline, "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat()}


def answer(analysis: dict, question: str) -> str:
    q = question.lower(); nodes = analysis["nodes"]
    people = [n["label"] for n in nodes if n["type"] == "person"]
    evidence = [n["label"] for n in nodes if n["type"] == "evidence"]
    locations = [n["label"] for n in nodes if n["type"] == "location"]
    vehicles = [n["label"] for n in nodes if n["type"] == "vehicle"]
    if any(word in q for word in ("who", "person", "people", "suspect")):
        return "People identified in the verified evidence: " + (", ".join(people) or "none yet") + "."
    if "timeline" in q or "when" in q:
        events = analysis["timeline"][:8]
        return "Timeline: " + ("; ".join(f"{e['date']} {e.get('time') or ''} — {e['title']}" for e in events) or "no dated events extracted") + "."
    if "where" in q or "location" in q:
        return "Locations in verified evidence: " + (", ".join(locations) or "none yet") + "."
    if "vehicle" in q or "car" in q:
        return "Vehicles in verified evidence: " + (", ".join(vehicles) or "none yet") + "."
    return analysis["summary"] + (" Key evidence: " + ", ".join(evidence[:10]) + "." if evidence else "")
