"""
schema.py — explicit Cold Case Connector ontology for Cognee's knowledge-graph extraction.

Cognee's `cognify()` accepts a `graph_model: BaseModel` (default `cognee.shared.data_models
.KnowledgeGraph`) that the extraction LLM is function-called against, plus an optional
`custom_prompt` describing how to fill it in. By subclassing Node/Edge with `Literal` types
instead of free-form strings, we force the LLM to only ever emit OUR node/edge vocabulary —
this is the "typed DataPoint schema" called for in the case-solver design doc (Version 2):

    Nodes:  Person, Location, TimePoint, Evidence, Object
    Edges:  WAS_AT, AT_TIME, DEPICTS, REPORTED_BY, CONTRADICTS

Usage (see memory_service.cognify):

    from backend.schema import ColdCaseGraph, COLD_CASE_EXTRACTION_PROMPT
    await cognee.cognify(datasets=[dataset], graph_model=ColdCaseGraph,
                          custom_prompt=COLD_CASE_EXTRACTION_PROMPT)

This is additive: cognify() still works with the default schema if graph_model is omitted,
so existing ingested datasets/behavior are unaffected unless callers opt in.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, field_validator

# Subclass Cognee's OWN Node/Edge/KnowledgeGraph (rather than independent BaseModels).
# Cognee's downstream graph-building/summarization tasks do isinstance()/structural checks
# against these exact classes, so a parallel schema fails deep in the pipeline with cryptic
# "Input should be a valid dictionary or instance of Entity" errors. Subclassing keeps full
# compatibility while still constraining `type`/`relationship_name` to our vocabulary via
# Literal overrides (Pydantic v2 allows narrowing a field's type in a subclass).
from cognee.shared.data_models import Node, Edge, KnowledgeGraph

NodeType = Literal["Case", "Person", "Location", "TimePoint", "Evidence", "Object"]

RelationshipName = Literal[
    "WAS_AT",       # Person -> Location
    "AT_TIME",      # Location -> TimePoint
    "DEPICTS",      # Evidence -> Person | Object | Location
    "REPORTED_BY",  # Evidence -> Person (lineage of who made the claim)
    "CONTRADICTS",  # Evidence -> Evidence (machine-flagged conflict)
    "INVOLVED_IN",  # Person -> Case (role/interest, not guilt)
    "OCCURRED_AT",  # Case -> Location
    "HAS_EVIDENCE", # Case -> Evidence
    "OBSERVED_AT",  # Person/Object -> Location, when explicitly reported
    "RELATES_TO",   # Evidence -> Person/Object/Location with provenance
    "EXAMINED",     # Person -> Evidence
]


class ColdCaseNode(Node):
    """A typed entity in the cold-case graph (case-solver doc v2, section 2). Extends
    Cognee's Node (id, name, type, description, label) with optional type-specific
    properties — populate only the ones relevant to `type`."""

    type: NodeType  # narrows Node.type: str -> our 5-value vocabulary

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value):
        return value or ""

    role: Optional[str] = Field(
        default=None, description="Person only: Suspect | Witness | Victim."
    )
    status: Optional[str] = Field(default=None, description="Person only: e.g. at-large, cleared.")
    coordinates: Optional[str] = Field(default=None, description="Location only: lat/long or address.")
    timestamp: Optional[str] = Field(default=None, description="TimePoint only: ISO-8601 if known.")
    raw_label: Optional[str] = Field(default=None, description="TimePoint only: e.g. '11:02 PM'.")
    evidence_type: Optional[str] = Field(
        default=None, description="Evidence only: Audio | Video | Photo | Text."
    )
    reliability_score: Optional[float] = Field(
        default=None, description="Evidence only: 0-1 confidence in this source."
    )
    category: Optional[str] = Field(default=None, description="Object only: Vehicle | Weapon | Tool | ...")


class ColdCaseEdge(Edge):
    """A typed relationship in the cold-case graph (case-solver doc v2, section 2). Extends
    Cognee's Edge (source_node_id, target_node_id, relationship_name, description) with
    `relationship_name` narrowed to our 5-edge vocabulary."""

    relationship_name: RelationshipName


class ColdCaseGraph(KnowledgeGraph):
    """Drop-in replacement for cognee.shared.data_models.KnowledgeGraph, constrained to the
    Cold Case Connector ontology so extraction is typed instead of free-form."""

    nodes: list[ColdCaseNode] = Field(default_factory=list)
    edges: list[ColdCaseEdge] = Field(default_factory=list)


COLD_CASE_EXTRACTION_PROMPT = """\
You are extracting a knowledge graph from police case files (narratives, forensic reports,
witness statements, financial/alibi records) for a cold-case investigation tool.
To leverage our hybrid vector-graph indexing system, resolve all ingested evidence into structured data points.
Map unstructured inputs into the following specific entities and explicit relational edges.

Node Definitions (DataPoint Subclasses):
- Person: The actors involved in the case. (id, name, role: Suspect/Witness/Victim, status)
- Location: Physical spatial points where events occurred. (id, name, coordinates: Lat/Long, type)
- TimePoint: Absolute chronological anchors. (id, timestamp, raw_label: e.g. "11:02 PM")
- Evidence: Metadata wrapper tracking the raw asset source and lineage. (id, type: Audio/Video/Photo/Text, file_url, extracted_text, reliability_score)
- Object: Material items relevant to the timeline. (id, description, category: Vehicle/Weapon, owner_id)
- Case: The investigation case file record.

Edge Definitions (Graph Relations):
  WAS_AT      (Person -> Location)       — Maps an individual's presence to a specific place.
  AT_TIME     (Location -> TimePoint)    — Binds a spatial presence to a distinct chronological window.
  DEPICTS     (Evidence -> Person|Object|Location) — Confirms an entity was verified inside a raw piece of evidence.
  REPORTED_BY (Evidence -> Person)       — Tracks the lineage of human assertions (who made the claim).
  CONTRADICTS (Evidence -> Evidence)     — Core Flag: Machine-generated conflict edge mapping direct impossibilities.
  INVOLVED_IN (Person -> Case)           — stated role/person of interest; never implies guilt
  OCCURRED_AT (Case -> Location)         — incident location explicitly stated in the record
  HAS_EVIDENCE (Case -> Evidence)        — verified evidence belongs to this case
  OBSERVED_AT (Person|Object -> Location)— an explicit sourced observation
  RELATES_TO (Evidence -> Person|Object|Location) — a source-backed evidentiary relationship
  EXAMINED (Person -> Evidence)           — named examiner handled/analyzed the evidence

For every Person, capture role (Suspect/Witness/Victim) and status if stated.
For every Location, capture coordinates/address if stated, and type of location.
For every TimePoint, capture the raw time label as written (e.g. "00:48", "11:02 PM") and a timestamp if inferable.
For every Evidence node, capture its type (Audio/Video/Photo/Text), file_url if present, extracted_text, and a reliability_score (float 0.0 to 1.0).
For every Object node, capture description, category (e.g. Vehicle/Weapon), and owner_id if stated.
Do not invent facts that are not present in the source text. Prefer precise, sourced edges
over speculative ones. Never create a relationship merely because two entities appear in the
same document. Preserve CASE_ID, EVIDENCE_ID, and SOURCE_FILE provenance in descriptions.
"""
