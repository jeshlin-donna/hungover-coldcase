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


def _add_node(nodes, kind, label, source=None, **extra):
    node_id = _id(kind, label)
    node = nodes.setdefault(node_id, {"id": node_id, "label": label.strip(), "type": kind, "sources": [], **extra})
    if source and source not in node["sources"]: node["sources"].append(source)
    for key, value in extra.items():
        if value is not None and not node.get(key): node[key] = value
    return node_id


def build(case: dict, evidence_items: list[dict]) -> dict:
    nodes, edges, edge_keys, timeline = {}, [], set(), []
    case_node = _add_node(nodes, "case", case["title"], status=case["status"])

    def edge(source, target, relation, source_doc=None, confidence="verified"):
        key = (source, target, relation)
        if source == target: return
        if key not in edge_keys:
            edge_keys.add(key); edges.append({"source": source, "target": target, "relation": relation,
                                               "sources": [source_doc] if source_doc else [], "confidence": confidence})
        elif source_doc:
            current = next(item for item in edges if (item["source"], item["target"], item["relation"]) == key)
            if source_doc not in current["sources"]: current["sources"].append(source_doc)

    for item in evidence_items:
        if item["status"] != "ingested": continue
        text = item.get("reviewed_text") or ""
        source = item["original_filename"]
        found, people, locations, vehicles, facts = [], [], [], [], []

        # Explicit labeled people are high-confidence and source-grounded.
        for match in re.finditer(r"(?im)^((?:primary\s+)?(?:suspect|examiner|victim|witness|name))\s*:\s*([^\n,]+)", text):
            role, label = match.group(1).strip().lower(), match.group(2).strip()
            if 2 <= len(label) <= 80:
                person = _add_node(nodes, "person", label, source, role="suspect" if "suspect" in role else role)
                found.append(person); people.append(person)
                edge(person, case_node, "person_of_interest_in" if "suspect" in role else "involved_in", source,
                     "reported" if "suspect" in role else "verified")
        # Inline role phrases and structured spreadsheet rows cover arbitrary
        # cases; no demo-person allowlist is used.
        inline_people = re.findall(
            r"\b((?i:suspect|witness|victim|examiner|officer|associate|accomplice))\s*:?[ \t]+"
            r"([A-Z][A-Za-z'-]+(?:[ \t]+[A-Z0-9][A-Za-z0-9#'-]*){1,3})",
            text,
        )
        table_people = re.findall(
            r"(?im)^\s*(.+?)[ \t]+(primary suspect|possible accomplice)\b",
            text,
        )
        for role, label in inline_people + [(role, label) for label, role in table_people]:
            label = label.strip()
            if not (2 <= len(label) <= 80): continue
            normalized_role = "suspect" if "suspect" in role.lower() else role.lower()
            person = _add_node(nodes, "person", label, source, role=normalized_role)
            found.append(person); people.append(person)
            edge(person, case_node, "person_of_interest_in" if normalized_role == "suspect" else "involved_in",
                 source, "reported")

        for match in re.finditer(r"(?im)^location\s*:\s*([^\n]+)", text):
            location = _add_node(nodes, "location", match.group(1).strip(), source)
            found.append(location); locations.append(location); edge(case_node, location, "occurred_at", source)
        for label in re.findall(r"\b\d{1,5}\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Ave|Avenue|St|Street|Rd|Road|Lane|Ln|Dr|Drive|Ct|Court)\b", text):
            location = _add_node(nodes, "location", label, source)
            found.append(location); locations.append(location); edge(case_node, location, "occurred_at", source)

        for label in re.findall(r"(?i)\b(?:dark\s+blue|black|white|red|silver|gray|grey)\s+(?:Honda|Toyota|Ford|Chevrolet|Nissan|BMW|Audi)?\s*[A-Z][A-Za-z0-9-]*(?:\s+Accord|\s+Civic|\s+sedan|\s+SUV)?(?:,?\s+partial\s+plate\s+[A-Z0-9-]+)?", text):
            if len(label.split()) >= 2:
                vehicle = _add_node(nodes, "vehicle", label.strip(" ,"), source)
                found.append(vehicle); vehicles.append(vehicle); edge(case_node, vehicle, "vehicle_reported", source, "reported")

        evidence_labels = []
        evidence_labels += re.findall(r"(?im)^Item\s+\d+\s*:\s*([^\n]+)", text)
        for match in re.finditer(r"(?im)^Key evidence\s*:\s*([^\n]+)", text):
            evidence_labels += [part.strip() for part in match.group(1).split(",")]
        evidence_labels += re.findall(r"(?i)\b8mm\s+left-nick\s+pry\s+blade\b", text)
        for label in evidence_labels:
            # A vehicle description belongs on the vehicle node; duplicating it as
            # an "evidence" node makes the board look connected without adding facts.
            if label and not re.search(r"(?i)\b(?:Honda|Toyota|Ford|Chevrolet|Nissan|BMW|Audi|sedan|SUV|Accord|Civic)\b", label):
                fact = _add_node(nodes, "evidence", label, source, evidence_type=item["modality"])
                found.append(fact); facts.append(fact); edge(case_node, fact, "has_evidence", source)

        # Only assert semantic entity-to-entity edges when the wording supports them.
        if re.search(r"(?i)observed|saw|sighted|parked|near|left the area", text):
            for vehicle in set(vehicles):
                for location in set(locations): edge(vehicle, location, "observed_near", source, "reported")
        if re.search(r"(?i)seen in (?:the )?vehicle|possible accomplice", text):
            for person in set(people):
                if "unknown associate" in nodes[person]["label"].lower():
                    for vehicle in set(vehicles): edge(person, vehicle, "seen_in", source, "reported")
        if re.search(r"(?i)tool-mark analysis|forensics report|forensic confirmation", text):
            examiners = [p for p in people if nodes[p].get("role") == "examiner"]
            for examiner in examiners:
                for fact in set(facts): edge(examiner, fact, "examined", source)

        dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text)
        # Structured CSV-like time/event rows.
        for tm, event, confidence in re.findall(r"(?m)^\s*(\d{2}:\d{2})\s+(.+?)\s+(0\.\d+|1\.0+)\s*$", text):
            timeline.append({"date": dates[0] if dates else case.get("incident_date"), "time": tm,
                             "title": event.strip(), "summary": f"Confidence {confidence}",
                             "evidence_id": item["id"], "source": item["original_filename"]})
        for date, location, amount, notes in re.findall(r"(?m)^\s*(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(\d+\.\d{2})\s+\d+\s+(.+)$", text):
            timeline.append({"date": date, "time": None, "title": notes.strip(),
                             "summary": f"{location.strip()} · ${amount}", "evidence_id": item["id"],
                             "source": item["original_filename"]})
        if dates and not any(event["evidence_id"] == item["id"] for event in timeline):
            timeline.append({"date": dates[0], "time": None, "title": item["original_filename"],
                             "summary": text.splitlines()[0][:180], "evidence_id": item["id"], "source": item["original_filename"]})

    timeline.sort(key=lambda event: (event.get("date") or "9999-12-31", event.get("time") or ""))
    people = [node for node in nodes.values() if node["type"] == "person"]
    evidence = [node for node in nodes.values() if node["type"] == "evidence"]
    summary = (f"{case['title']} contains {len(evidence_items)} verified source files, "
               f"{len(people)} identified people, {len(evidence)} evidence items, "
               f"and {len(timeline)} dated or timed events.")
    return {"case_id": case["id"], "graph_revision": case["graph_revision"], "nodes": list(nodes.values()),
            "edges": edges, "timeline": timeline, "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat()}


def knowledge_packet(case: dict, item: dict) -> str:
    """Canonical payload sent to Cognee; confirmed content is separated from provenance."""
    return f"""VERIFIED CASE EVIDENCE RECORD
CASE_ID: {case['id']}
CASE_TITLE: {case['title']}
EVIDENCE_ID: {item['id']}
SOURCE_FILE: {item['original_filename']}
MODALITY: {item['modality']}
REVIEW_STATUS: investigator_confirmed

INVESTIGATOR_CONTEXT:
{item.get('context') or '[none provided]'}

CONFIRMED_CONTENT:
{item.get('reviewed_text') or ''}

PROVENANCE_RULE: Every extracted entity and relationship must remain attributable to EVIDENCE_ID and SOURCE_FILE. Do not infer guilt or convert co-occurrence into a factual relationship.
"""


def answer(analysis: dict, question: str) -> str:
    q = question.lower(); nodes = analysis["nodes"]
    people = [n["label"] for n in nodes if n["type"] == "person"]
    evidence = [n["label"] for n in nodes if n["type"] == "evidence"]
    locations = [n["label"] for n in nodes if n["type"] == "location"]
    vehicles = [n["label"] for n in nodes if n["type"] == "vehicle"]
    if any(word in q for word in ("who", "person", "people", "suspect")):
        people_with_roles = [f"{n['label']} ({n.get('role') or 'role not established'})" for n in nodes if n["type"] == "person"]
        return "People identified in the verified evidence: " + (", ".join(people_with_roles) or "none yet") + "."
    if "timeline" in q or "when" in q:
        events = analysis["timeline"][:8]
        return "Timeline: " + ("; ".join(f"{e['date']} {e.get('time') or ''} — {e['title']}" for e in events) or "no dated events extracted") + "."
    if "where" in q or "location" in q:
        return "Locations in verified evidence: " + (", ".join(locations) or "none yet") + "."
    if "vehicle" in q or "car" in q:
        return "Vehicles in verified evidence: " + (", ".join(vehicles) or "none yet") + "."
    return analysis["summary"] + (" Key evidence: " + ", ".join(evidence[:10]) + "." if evidence else "")


def sources_for_question(analysis: dict, question: str) -> list[str]:
    """Return the verified filenames most relevant to a case-tool question."""
    q = question.lower()
    if "timeline" in q or "when" in q:
        return list(dict.fromkeys(event["source"] for event in analysis["timeline"] if event.get("source")))
    kinds = None
    if any(word in q for word in ("who", "person", "people", "suspect", "witness", "examiner")): kinds = {"person"}
    elif "where" in q or "location" in q: kinds = {"location"}
    elif "vehicle" in q or "car" in q: kinds = {"vehicle"}
    elif "evidence" in q or "tool" in q: kinds = {"evidence"}
    selected = [node for node in analysis["nodes"] if kinds is None or node["type"] in kinds]
    return list(dict.fromkeys(source for node in selected for source in node.get("sources", [])))[:20]
