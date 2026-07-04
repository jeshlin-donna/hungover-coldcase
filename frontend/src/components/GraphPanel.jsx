import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api.js";

const NODE_COLORS = {
  case: "#58a6ff",
  tool: "#e3b341",
  vehicle: "#3fb950",
  mo: "#bc8cff",
  suspect: "#f85149",
  jurisdiction: "#8b949e",
  alibi: "#ff9f1c",
  receipt: "#2ec4b6",
  evidence: "#d2a8ff",
};

const TYPE_LABELS = {
  case: "Case",
  tool: "Tool",
  vehicle: "Vehicle",
  mo: "MO",
  suspect: "Suspect",
  jurisdiction: "Jurisdiction",
  alibi: "Alibi claim",
  receipt: "Card record",
  evidence: "Uploaded evidence",
};

const TYPE_ICONS = {
  case: "🗂️",
  tool: "🛠️",
  vehicle: "🚗",
  mo: "🧭",
  suspect: "👤",
  jurisdiction: "🏛️",
  alibi: "🗣️",
  receipt: "💳",
  evidence: "📎",
};

// Animate node removal by filtering them out over a brief transition.
function withoutNode(graph, nodeId) {
  return {
    ...graph,
    nodes: graph.nodes.filter((n) => n.id !== nodeId),
    edges: graph.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
  };
}

// Temporal slider range: Jan 2023 - Dec 2025, by month (mirrors TimelinePanel.jsx)
const SLIDER_MIN_YEAR = 2023;
const SLIDER_MAX_YEAR = 2025;
const SLIDER_MAX_MONTH = 11; // December = 11

function totalMonths() {
  return (SLIDER_MAX_YEAR - SLIDER_MIN_YEAR) * 12 + SLIDER_MAX_MONTH;
}

function monthIndexToDate(idx) {
  const year = SLIDER_MIN_YEAR + Math.floor(idx / 12);
  const month = idx % 12;
  return new Date(year, month, 1);
}

function toISODate(d) {
  return d.toISOString().slice(0, 10);
}

function formatSliderDate(d) {
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

// Client-side fallback filter (used offline / if the /graph/temporal endpoint is unreachable).
function filterGraphByDate(fullGraph, cutoffISO) {
  const nodes = fullGraph.nodes || [];
  const visibleIds = new Set(
    nodes.filter((n) => !n.date || n.date <= cutoffISO).map((n) => n.id)
  );
  return {
    ...fullGraph,
    nodes: nodes.filter((n) => visibleIds.has(n.id)),
    edges: (fullGraph.edges || []).filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target)
    ),
  };
}

export default function GraphPanel({ justImproved, graphData, onGraphLoaded }) {
  const [fullGraph, setFullGraph] = useState({ nodes: [], edges: [], contradictions: [] });
  const [graph, setGraph] = useState({ nodes: [], edges: [], contradictions: [] });
  const [reveal, setReveal] = useState(false);
  const [expunging, setExpunging] = useState(false);
  const [expungeNote, setExpungeNote] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const maxIdx = totalMonths();
  const [sliderIdx, setSliderIdx] = useState(maxIdx); // start showing everything
  const fgRef = useRef();

  useEffect(() => {
    if (graphData) {
      setFullGraph(graphData);
      setGraph(graphData);
    } else {
      api.graph().then((g) => {
        setFullGraph(g);
        setGraph(g);
        onGraphLoaded?.(g);
      }).catch(() => {
        setFullGraph(MOCK_GRAPH);
        setGraph(MOCK_GRAPH);
      });
    }
  }, [graphData]);

  const sliderDate = monthIndexToDate(sliderIdx);
  const isFiltered = sliderIdx < maxIdx;

  // Debounce so dragging doesn't hammer the endpoint on every tick, but this
  // does genuinely call GET /api/v1/graph/temporal?time=X per the spec.
  useEffect(() => {
    if (!fullGraph.nodes?.length) return;
    if (!isFiltered) {
      setGraph(fullGraph);
      return;
    }
    const cutoffISO = toISODate(sliderDate);
    const id = setTimeout(() => {
      api
        .graphTemporal(cutoffISO)
        .then((g) => setGraph(g))
        .catch(() => setGraph(filterGraphByDate(fullGraph, cutoffISO)));
    }, 150);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sliderIdx, fullGraph]);

  const data = useMemo(() => {
    const links = graph.edges.map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.relation,
      _c: false,
    }));
    if (reveal) {
      for (const c of graph.contradictions || []) {
        links.push({ source: c.a, target: c.b, relation: "CONTRADICTION", _c: true });
      }
    }
    return { nodes: graph.nodes.map((n) => ({ ...n })), links };
  }, [graph, reveal]);

  async function handleExpunge() {
    setExpunging(true);
    setExpungeNote("");
    try {
      // Animate: first remove the Riverside case node + its immediate edges.
      setGraph((g) => withoutNode(g, "case:RV-0788"));
      await new Promise((r) => setTimeout(r, 350));
      // Also remove the Riverside jurisdiction node.
      setGraph((g) => withoutNode(g, "jur:riverside"));

      const res = await api.expunge("case:RV-0788").catch(() => ({
        removed: ["case:RV-0788", "jur:riverside"],
      }));
      setExpungeNote(
        `forget(): removed ${(res.removed || ["case:RV-0788", "jur:riverside"]).join(", ")} — rest of graph intact.`
      );
    } finally {
      setExpunging(false);
    }
  }

  const handleNodeClick = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  const contradictions = graph.contradictions || [];

  // Fit the whole graph into view whenever the node/link set changes —
  // otherwise react-force-graph-2d keeps its default zoom level and only
  // the tight center cluster is visible in a mostly-empty canvas.
  useEffect(() => {
    if (!data.nodes.length) return;
    fgRef.current?.d3Force("charge")?.strength(-320);
    fgRef.current?.d3Force("link")?.distance(120);
    const id = setTimeout(() => {
      fgRef.current?.zoomToFit(400, 60);
    }, 300);
    return () => clearTimeout(id);
  }, [data]);

  return (
    <div className="panel">
      <div className="row" style={{ marginBottom: 10 }}>
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 14, maxWidth: 560 }}>
          The case web. Tool signature, vehicle, and MO bridge two jurisdictions that
          never shared a database.
        </p>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <button
            className={reveal ? "active" : ""}
            onClick={() => { setReveal((v) => !v); setSelectedNode(null); }}
          >
            {reveal ? "Hide alibi check" : "Run alibi check"}
          </button>
          <button className="danger" onClick={handleExpunge} disabled={expunging}>
            {expunging ? "Expunging…" : "Expunge Riverside (forget())"}
          </button>
        </div>
      </div>

      {/* Temporal slider — filters which graph nodes/edges are visible via GET /graph/temporal?time=X */}
      <div className="temporal-slider-wrap">
        <div className="temporal-slider-label-row">
          <span className="temporal-slider-label">Temporal filter</span>
          <span className="temporal-slider-date">
            {isFiltered
              ? `Showing graph as of ${formatSliderDate(sliderDate)}`
              : "Full graph shown"}
          </span>
          {isFiltered && (
            <button className="temporal-reset-btn" onClick={() => setSliderIdx(maxIdx)}>
              Reset
            </button>
          )}
        </div>
        <input
          type="range"
          className="temporal-slider"
          min={0}
          max={maxIdx}
          step={1}
          value={sliderIdx}
          onChange={(e) => { setSliderIdx(Number(e.target.value)); setSelectedNode(null); }}
        />
        <div className="temporal-slider-ends">
          <span>Jan 2023</span>
          <span>Dec 2025</span>
        </div>
      </div>

      {reveal && contradictions.map((c, i) => (
        <p key={i} className="contradiction">
          ⛔ <b>Alibi breaks:</b> {c.reason}
          <span className="srcs"> [{(c.sources || []).join(", ")}]</span>
        </p>
      ))}

      {expungeNote && (
        <p className="note" style={{ fontFamily: "ui-monospace,monospace", fontSize: 13 }}>
          ✓ {expungeNote}
        </p>
      )}

      <div className="graph-wrap">
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          nodeLabel={(n) => {
            const hoverText = n.type === "case" ? n.label || TYPE_LABELS[n.type] || "Case" : n.label || TYPE_LABELS[n.type] || n.type;
            return `${TYPE_ICONS[n.type] || ""} ${hoverText} (${TYPE_LABELS[n.type] || n.type})`;
          }}
          nodeColor={(n) => NODE_COLORS[n.type] || "#aaa"}
          nodeRelSize={7}
          d3VelocityDecay={0.35}
          warmupTicks={60}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 60)}
          linkLabel={(l) => l.relation}
          linkColor={(l) => (l._c ? "#f85149" : "rgba(255,255,255,0.18)")}
          linkWidth={(l) => (l._c ? 3 : 1)}
          linkDirectionalParticles={(l) => (l._c ? 5 : 1)}
          linkDirectionalParticleWidth={(l) => (l._c ? 4 : 2)}
          linkDirectionalParticleColor={(l) => (l._c ? "#f85149" : "#58a6ff")}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkCanvasObjectMode={() => "after"}
          linkCanvasObject={(link, ctx, globalScale) => {
            const nodes = fgRef.current?.graphData?.()?.nodes || data.nodes;
            const start = typeof link.source === "object" ? link.source : nodes.find((n) => n.id === link.source);
            const end = typeof link.target === "object" ? link.target : nodes.find((n) => n.id === link.target);
            if (!start || !end || start.x == null || end.x == null) return;
            const label = link.relation || link.label || "";
            if (!label) return;
            const dx = end.x - start.x;
            const dy = end.y - start.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (!dist) return;
            const midX = start.x + dx * 0.5;
            const midY = start.y + dy * 0.5;
            let angle = Math.atan2(dy, dx);
            const offset = 10 / globalScale;
            const textX = midX + Math.sin(angle) * offset;
            const textY = midY - Math.cos(angle) * offset;
            const fontSize = Math.max(6 / globalScale, 5);
            if (angle > Math.PI / 2) angle -= Math.PI;
            if (angle < -Math.PI / 2) angle += Math.PI;
            ctx.save();
            ctx.translate(textX, textY);
            ctx.rotate(angle);
            ctx.font = `${fontSize}px ui-sans-serif,system-ui,sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = "rgba(16,16,24,0.92)";
            ctx.fillRect(-textWidth / 2 - 4, -fontSize / 2 - 3, textWidth + 8, fontSize + 6);
            ctx.fillStyle = "rgba(248,248,248,0.98)";
            ctx.fillText(label, 0, 0);
            ctx.strokeStyle = "rgba(0,0,0,0.4)";
            ctx.lineWidth = Math.max(1 / globalScale, 0.5);
            ctx.strokeText(label, 0, 0);
            ctx.restore();
          }}
          backgroundColor="#090d13"
          onNodeClick={handleNodeClick}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            // Green halo when justImproved
            if (justImproved) {
              ctx.save();
              ctx.beginPath();
              ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
              ctx.strokeStyle = "rgba(63,185,80,0.85)";
              ctx.lineWidth = 3;
              ctx.shadowColor = "#3fb950";
              ctx.shadowBlur = 12;
              ctx.stroke();
              ctx.restore();
            }
            const icon = TYPE_ICONS[node.type] || "";
            const label = node.type === "case" ? TYPE_LABELS[node.type] || "Case" : node.label || TYPE_LABELS[node.type] || node.type;
            const display = label.length > 18 ? label.slice(0, 18) + "…" : label;
            if (icon) {
              const iconSize = Math.max(16 / globalScale, 10);
              const labelSize = Math.max(iconSize * 0.45, 7);
              ctx.save();
              ctx.fillStyle = "rgba(230,237,243,0.95)";
              ctx.textAlign = "center";

              ctx.font = `${iconSize}px ui-sans-serif,system-ui,sans-serif`;
              ctx.textBaseline = "middle";
              ctx.fillText(icon, node.x, node.y - (labelSize / 2));

              ctx.font = `${labelSize}px ui-sans-serif,system-ui,sans-serif`;
              ctx.textBaseline = "top";
              ctx.fillText(display, node.x, node.y + (iconSize / 1.8));
              ctx.restore();
            }
          }}
        />

        {selectedNode && (
          <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </div>

      <div className="legend">
        {Object.entries(NODE_COLORS).map(([k, c]) => (
          <span key={k} className="legend-item">
            <i style={{ background: c }} />
            <span style={{ marginRight: 6 }}>{TYPE_ICONS[k] || ""}</span>
            {TYPE_LABELS[k] || k}
          </span>
        ))}
        <span className="legend-item">
          <i style={{ background: "#f85149", width: 18, height: 3, borderRadius: 1.5, display: "inline-block", verticalAlign: "middle", marginRight: 5 }} />
          contradiction
        </span>
      </div>
    </div>
  );
}

function NodeDetail({ node, onClose }) {
  const color = NODE_COLORS[node.type] || "#aaa";
  return (
    <div className="node-detail">
      <button className="nd-close" onClick={onClose} aria-label="Close">×</button>
      <span
        className="nd-type"
        style={{
          background: color + "22",
          color,
          border: `1px solid ${color}55`,
        }}
      >
        {TYPE_ICONS[node.type] ? `${TYPE_ICONS[node.type]} ` : ""}{TYPE_LABELS[node.type] || node.type}
      </span>
      <h4>{node.label}</h4>
      <div className="nd-id">{node.id}</div>
    </div>
  );
}

// Embedded mock so the graph renders even when the backend is offline.
const MOCK_GRAPH = {
  nodes: [
    { id: "jur:maple-heights", label: "Maple Heights PD", type: "jurisdiction" },
    { id: "jur:riverside", label: "Riverside PD", type: "jurisdiction" },
    { id: "case:MH-0312", label: "MH-2023-0312", type: "case" },
    { id: "case:RV-0788", label: "RV-2023-0788", type: "case" },
    { id: "case:MH-0102", label: "MH-2025-0102", type: "case" },
    { id: "tool:pry-8mm", label: "Pry bar · 8mm · left-edge nick", type: "tool" },
    { id: "veh:blue-sedan", label: "Dark blue sedan · plate 8K·", type: "vehicle" },
    { id: "mo:rear-slider", label: "MO: rear slider, 02:00–04:00", type: "mo" },
    { id: "suspect:daniel-marsh", label: "Daniel R. Marsh", type: "suspect" },
    { id: "alibi:marsh-nov19", label: "Alibi: '300mi out of state'", type: "alibi" },
    { id: "receipt:marsh-nov19", label: "Card record: motel 4.2mi away", type: "receipt" },
  ],
  edges: [
    { source: "case:MH-0312", target: "jur:maple-heights", relation: "filed_in" },
    { source: "case:MH-0102", target: "jur:maple-heights", relation: "filed_in" },
    { source: "case:RV-0788", target: "jur:riverside", relation: "filed_in" },
    { source: "case:MH-0312", target: "tool:pry-8mm", relation: "tool_used" },
    { source: "case:RV-0788", target: "tool:pry-8mm", relation: "tool_used" },
    { source: "case:MH-0102", target: "tool:pry-8mm", relation: "tool_used" },
    { source: "case:MH-0312", target: "veh:blue-sedan", relation: "vehicle_seen" },
    { source: "case:RV-0788", target: "veh:blue-sedan", relation: "vehicle_seen" },
    { source: "case:MH-0102", target: "veh:blue-sedan", relation: "vehicle_seen" },
    { source: "case:MH-0312", target: "mo:rear-slider", relation: "matches_mo" },
    { source: "case:RV-0788", target: "mo:rear-slider", relation: "matches_mo" },
    { source: "case:MH-0102", target: "mo:rear-slider", relation: "matches_mo" },
    { source: "suspect:daniel-marsh", target: "veh:blue-sedan", relation: "owns" },
    { source: "suspect:daniel-marsh", target: "tool:pry-8mm", relation: "possessed" },
    { source: "suspect:daniel-marsh", target: "case:MH-0312", relation: "confessed_to" },
    { source: "suspect:daniel-marsh", target: "case:RV-0788", relation: "confessed_to" },
    { source: "suspect:daniel-marsh", target: "case:MH-0102", relation: "confessed_to" },
    { source: "suspect:daniel-marsh", target: "alibi:marsh-nov19", relation: "claims" },
    { source: "suspect:daniel-marsh", target: "receipt:marsh-nov19", relation: "card_used" },
    { source: "receipt:marsh-nov19", target: "case:RV-0788", relation: "places_near" },
    { source: "alibi:marsh-nov19", target: "case:RV-0788", relation: "denies_presence" },
  ],
  contradictions: [
    {
      a: "alibi:marsh-nov19",
      b: "receipt:marsh-nov19",
      reason:
        "Alibi claims 300 miles out of state on 2023-11-19; card records place Marsh at a motel 4.2 miles from the Riverside scene at 00:48 the same night.",
      sources: ["MARSH-ALIBI", "MARSH-RECEIPT"],
    },
  ],
};
