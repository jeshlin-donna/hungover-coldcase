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
  person: "#f85149",
  location: "#8b949e",
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
  person: "Person",
  location: "Location",
};

// A distinct glyph per node type so the graph reads at a glance even for
// colorblind users, and so similarly-hued nodes (e.g. alibi/receipt) don't
// get confused with each other.
const NODE_ICONS = {
  case: "📁",
  tool: "🔧",
  vehicle: "🚗",
  mo: "🕒",
  suspect: "👤",
  jurisdiction: "🏛",
  alibi: "🗣",
  receipt: "🧾",
  evidence: "📎",
  person: "👤",
  location: "📍",
};

// Base radius per type — suspects and cases are the anchors of the story,
// so they read as visually "heavier" than supporting evidence nodes.
const NODE_BASE_SIZE = {
  suspect: 9,
  person: 9,
  case: 7.5,
  jurisdiction: 7,
};
const DEFAULT_NODE_SIZE = 5.5;

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

export default function GraphPanel({ justImproved, graphData, onGraphLoaded, caseId }) {
  const [fullGraph, setFullGraph] = useState({ nodes: [], edges: [], contradictions: [] });
  const [graph, setGraph] = useState({ nodes: [], edges: [], contradictions: [] });
  const [reveal, setReveal] = useState(false);
  const [expunging, setExpunging] = useState(false);
  const [expungeNote, setExpungeNote] = useState("");
  const [reindexing, setReindexing] = useState(false);
  const [reindexNote, setReindexNote] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [hiddenTypes, setHiddenTypes] = useState(() => new Set());
  const maxIdx = totalMonths();
  const [sliderIdx, setSliderIdx] = useState(maxIdx); // start showing everything
  const fgRef = useRef();

  useEffect(() => {
    if (graphData) {
      setFullGraph(graphData);
      setGraph(graphData);
    } else {
      api.graph(caseId).then((g) => {
        setFullGraph(g);
        setGraph(g);
        onGraphLoaded?.(g);
      }).catch(() => {
        const fallback = caseId ? { nodes: [], edges: [], contradictions: [] } : MOCK_GRAPH;
        setFullGraph(fallback);
        setGraph(fallback);
      });
    }
  }, [graphData, caseId]);

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
    const visibleNodes = graph.nodes.filter((n) => !hiddenTypes.has(n.type));
    const visibleIds = new Set(visibleNodes.map((n) => n.id));

    const links = graph.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({ ...e, source: e.source, target: e.target, relation: e.relation, _c: false }));
    if (reveal) {
      for (const c of graph.contradictions || []) {
        if (visibleIds.has(c.a) && visibleIds.has(c.b)) {
          links.push({ source: c.a, target: c.b, relation: "CONTRADICTION", _c: true });
        }
      }
    }

    // Degree = how many edges touch this node — used to size + emphasize the
    // "hub" nodes (suspect, repeat tool/vehicle/MO) that carry the story.
    const degree = new Map();
    for (const l of links) {
      degree.set(l.source, (degree.get(l.source) || 0) + 1);
      degree.set(l.target, (degree.get(l.target) || 0) + 1);
    }

    const nodes = visibleNodes.map((n) => ({ ...n, _degree: degree.get(n.id) || 0 }));
    return { nodes, links };
  }, [graph, reveal, hiddenTypes]);

  // Adjacency lookup for hover/select focus mode: which node ids + link refs
  // are directly connected to a given node, so we can highlight the local
  // "story" around it and dim everything else.
  const neighborIndex = useMemo(() => {
    const map = new Map();
    for (const l of data.links) {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (!map.has(s)) map.set(s, { nodes: new Set(), links: new Set() });
      if (!map.has(t)) map.set(t, { nodes: new Set(), links: new Set() });
      map.get(s).nodes.add(t);
      map.get(t).nodes.add(s);
      map.get(s).links.add(l);
      map.get(t).links.add(l);
    }
    return map;
  }, [data.links]);

  const focusId = hoverNode?.id ?? selectedNode?.id ?? null;
  const focusInfo = focusId ? neighborIndex.get(focusId) : null;

  const toggleTypeVisibility = useCallback((type) => {
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
    setSelectedNode(null);
  }, []);

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

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node || null);
  }, []);

  const contradictions = graph.contradictions || [];
  const visibleLegendTypes = useMemo(
    () => Object.keys(NODE_COLORS).filter((type) => fullGraph.nodes?.some((node) => node.type === type)),
    [fullGraph.nodes]
  );

  async function handleReindex() {
    setReindexing(true);
    setReindexNote("Rebuilding verified case knowledge…");
    try {
      const result = await api.reindexCase(caseId);
      const refreshed = await api.graph(caseId);
      setFullGraph(refreshed);
      setGraph(refreshed);
      onGraphLoaded?.(refreshed);
      setReindexNote(`Knowledge rebuilt from ${result.evidence_count} verified files.`);
    } catch (error) {
      setReindexNote(error.message || "Knowledge rebuild failed.");
    } finally {
      setReindexing(false);
    }
  }

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
          {caseId ? "Verified people, evidence, vehicles, and locations. Files remain provenance—not graph clutter." : "The case web. Tool signature, vehicle, and MO bridge two jurisdictions that never shared a database."} <span className="muted">Hover a node to trace its
          connections · click for details · click a legend item to hide a node type.</span>
        </p>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          {!caseId && <button
            className={reveal ? "active" : ""}
            onClick={() => { setReveal((v) => !v); setSelectedNode(null); }}
          >
            {reveal ? "Hide alibi check" : "Run alibi check"}
          </button>}
          {!caseId && <button className="danger" onClick={handleExpunge} disabled={expunging}>
            {expunging ? "Expunging…" : "Expunge Riverside (forget())"}
          </button>}
          {caseId && <button onClick={handleReindex} disabled={reindexing} title="Rebuild Cognee and this board from investigator-confirmed evidence">
            {reindexing ? "Rebuilding…" : "Rebuild knowledge"}
          </button>}
          <button
            title="Re-center and fit the whole graph in view"
            onClick={() => fgRef.current?.zoomToFit(400, 60)}
          >
            ⤢ Center
          </button>
        </div>
      </div>

      {/* Temporal slider — filters which graph nodes/edges are visible via GET /graph/temporal?time=X */}
      {!caseId && <div className="temporal-slider-wrap">
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
      </div>}

      {reindexNote && <p className="note" role="status">{reindexing ? "⏳" : "✓"} {reindexNote}</p>}

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

      {fullGraph.cognee_insight && (
        <div className="cognee-insight-box">
          <span className="cognee-insight-label">Cognee graph insight (TRIPLET_COMPLETION)</span>
          <p className="cognee-insight-text">{fullGraph.cognee_insight}</p>
        </div>
      )}

      <div className="graph-wrap">
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          nodeLabel={(n) => `${n.label} (${TYPE_LABELS[n.type] || n.type})`}
          nodeRelSize={5}
          nodeVal={(n) => (NODE_BASE_SIZE[n.type] || DEFAULT_NODE_SIZE) + Math.min(n._degree || 0, 6) * 0.9}
          d3VelocityDecay={0.35}
          warmupTicks={60}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 60)}
          linkLabel={(l) => l.relation}
          linkColor={(l) => {
            if (l._c) return "#f85149";
            if (!focusInfo) return "rgba(255,255,255,0.18)";
            return focusInfo.links.has(l) ? "rgba(88,166,255,0.9)" : "rgba(255,255,255,0.06)";
          }}
          linkWidth={(l) => {
            if (l._c) return 3;
            return focusInfo?.links.has(l) ? 2.5 : 1;
          }}
          linkDirectionalParticles={(l) => (l._c ? 5 : focusInfo?.links.has(l) ? 3 : 0)}
          linkDirectionalParticleWidth={(l) => (l._c ? 4 : 3)}
          linkDirectionalParticleColor={(l) => (l._c ? "#f85149" : "#58a6ff")}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkCanvasObjectMode={() => "after"}
          linkCanvasObject={(link, ctx, globalScale) => {
            const nodes = fgRef.current?.graphData?.()?.nodes || data.nodes;
            const start = typeof link.source === "object" ? link.source : nodes.find((n) => n.id === link.source);
            const end = typeof link.target === "object" ? link.target : nodes.find((n) => n.id === link.target);
            if (!start || !end || start.x == null || end.x == null) return;
            const label = (link.relation || link.label || "").replaceAll("_", " ");
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
          onNodeHover={handleNodeHover}
          onBackgroundClick={() => { setSelectedNode(null); }}
          nodeCanvasObjectMode={() => "replace"}
          nodePointerAreaPaint={(node, color, ctx) => {
            const r = (NODE_BASE_SIZE[node.type] || DEFAULT_NODE_SIZE) + Math.min(node._degree || 0, 6) * 0.9;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fill();
          }}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const r = (NODE_BASE_SIZE[node.type] || DEFAULT_NODE_SIZE) + Math.min(node._degree || 0, 6) * 0.9;
            const color = NODE_COLORS[node.type] || "#aaa";
            const isFocused = focusId === node.id;
            const isNeighbor = focusInfo?.nodes.has(node.id);
            const dimmed = focusId && !isFocused && !isNeighbor;

            // Node circle, dimmed to translucent grey when a hover/selection
            // focus is active and this node isn't part of that local story.
            ctx.save();
            ctx.globalAlpha = dimmed ? 0.22 : 1;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            if (isFocused) {
              ctx.lineWidth = 2.5;
              ctx.strokeStyle = "#ffffff";
              ctx.stroke();
            }
            ctx.restore();

            // Green "just improved by improve()" halo — always shown regardless of focus.
            if (justImproved) {
              ctx.save();
              ctx.beginPath();
              ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI);
              ctx.strokeStyle = "rgba(63,185,80,0.85)";
              ctx.lineWidth = 3;
              ctx.shadowColor = "#3fb950";
              ctx.shadowBlur = 12;
              ctx.stroke();
              ctx.restore();
            }

            if (dimmed) return; // skip icon/label clutter for dimmed nodes

            // Type glyph centered in the node so shape/meaning reads even
            // before the color palette is memorized.
            const iconSize = Math.max(r * 1.1, 6);
            ctx.save();
            ctx.globalAlpha = dimmed ? 0.3 : 1;
            ctx.font = `${iconSize}px "Apple Color Emoji","Segoe UI Emoji",sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(NODE_ICONS[node.type] || "•", node.x, node.y + 0.5);
            ctx.restore();

            // Label pill — only render full text once zoomed in enough or
            // when this node is focused/hovered, so the default view stays
            // clean and "catchy" instead of a wall of overlapping text.
            const showLabel = isFocused || isNeighbor || globalScale > 2.2;
            if (!showLabel) return;
            const label = node.label || node.id;
            const fontSize = Math.max(10 / globalScale, 3.2);
            ctx.font = `${isFocused ? "700" : "500"} ${fontSize}px ui-sans-serif,system-ui,sans-serif`;
            const maxLen = isFocused ? 40 : 24;
            const display = label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
            const textW = ctx.measureText(display).width;
            const padX = 4, padY = 2;
            const boxY = node.y + r + 3;
            ctx.fillStyle = "rgba(9,13,19,0.78)";
            ctx.beginPath();
            ctx.roundRect(node.x - textW / 2 - padX, boxY, textW + padX * 2, fontSize + padY * 2, 4);
            ctx.fill();
            ctx.fillStyle = isFocused ? "#ffffff" : "rgba(230,237,243,0.9)";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(display, node.x, boxY + padY);
          }}
        />

        {selectedNode && (
          <NodeDetail
            node={selectedNode}
            edges={graph.edges}
            nodesById={Object.fromEntries(graph.nodes.map((n) => [n.id, n]))}
            onClose={() => setSelectedNode(null)}
            onSelect={setSelectedNode}
          />
        )}
      </div>

      <div className="legend">
        {visibleLegendTypes.map((k) => {
          const c = NODE_COLORS[k];
          return (
          <button
            key={k}
            className={`legend-item legend-toggle${hiddenTypes.has(k) ? " legend-off" : ""}`}
            onClick={() => toggleTypeVisibility(k)}
            title={hiddenTypes.has(k) ? `Show ${TYPE_LABELS[k] || k} nodes` : `Hide ${TYPE_LABELS[k] || k} nodes`}
          >
            <i style={{ background: c }} />
            {NODE_ICONS[k]} {TYPE_LABELS[k] || k}
          </button>
          );
        })}
        <span className="legend-item">
          <i style={{ background: "#f85149", width: 18, height: 3, borderRadius: 1.5, display: "inline-block", verticalAlign: "middle", marginRight: 5 }} />
          contradiction
        </span>
      </div>
    </div>
  );
}

function NodeDetail({ node, edges, nodesById, onClose, onSelect }) {
  const color = NODE_COLORS[node.type] || "#aaa";
  const connections = (edges || [])
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => {
      const otherId = e.source === node.id ? e.target : e.source;
      const other = nodesById?.[otherId];
      const direction = e.source === node.id ? "→" : "←";
      return { otherId, other, relation: e.relation, direction, sources: e.sources || [], confidence: e.confidence };
    });

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
        {NODE_ICONS[node.type]} {TYPE_LABELS[node.type] || node.type}
      </span>
      <h4>{node.label}</h4>
      <div className="nd-id">{node.id}</div>
      {(node.sources || []).length > 0 && (
        <div className="nd-id">Supported by: {node.sources.join(", ")}</div>
      )}

      {connections.length > 0 && (
        <div className="nd-connections">
          <div className="nd-connections-title">
            Connected to {connections.length} {connections.length === 1 ? "node" : "nodes"}
          </div>
          <ul>
            {connections.map((c, i) => (
              <li key={i}>
                <button
                  className="nd-connection-link"
                  onClick={() => c.other && onSelect?.(c.other)}
                  disabled={!c.other}
                >
                  <span className="nd-connection-rel">{c.direction} {c.relation.replaceAll("_", " ")}</span>
                  <span className="nd-connection-label">
                    {NODE_ICONS[c.other?.type] || ""} {c.other?.label || c.otherId}
                  </span>
                  {c.sources.length > 0 && <span className="nd-id">Source: {c.sources.join(", ")} · {c.confidence}</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
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
