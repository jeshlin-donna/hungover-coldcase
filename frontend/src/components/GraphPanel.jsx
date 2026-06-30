import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api.js";

const COLORS = {
  case: "#ff6b6b", tool: "#ffd93d", vehicle: "#6bcB77", mo: "#4d96ff",
  suspect: "#c77dff", jurisdiction: "#8d99ae", alibi: "#ff9f1c", receipt: "#2ec4b6",
};

export default function GraphPanel() {
  const [graph, setGraph] = useState({ nodes: [], edges: [], contradictions: [] });
  const [reveal, setReveal] = useState(false);
  const [note, setNote] = useState("");
  const fgRef = useRef();

  useEffect(() => { api.graph().then(setGraph); }, []);

  // Build force-graph data; when "reveal" is on, inject red CONTRADICTION links.
  const data = useMemo(() => {
    const links = graph.edges.map((e) => ({
      source: e.source, target: e.target, relation: e.relation, _c: false,
    }));
    if (reveal) {
      for (const c of graph.contradictions || []) {
        links.push({ source: c.a, target: c.b, relation: "CONTRADICTION", _c: true });
      }
    }
    return { nodes: graph.nodes.map((n) => ({ ...n })), links };
  }, [graph, reveal]);

  async function expunge() {
    const res = await api.expunge("case:RV-0788");
    setGraph((g) => ({ ...g, ...res.graph }));
    setNote(`forget(): removed ${res.removed.join(", ") || "the sealed subgraph"} — rest intact.`);
  }

  return (
    <div className="panel">
      <div className="row">
        <p>The case web. Tool signature, vehicle, and MO bridge two jurisdictions that
          never shared a database.</p>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={reveal ? "active" : ""} onClick={() => setReveal((v) => !v)}>
            {reveal ? "Hide alibi check" : "Run alibi check"}
          </button>
          <button className="danger" onClick={expunge}>Expunge Riverside (forget)</button>
        </div>
      </div>

      {reveal && (graph.contradictions || []).map((c, i) => (
        <p key={i} className="contradiction">⛔ <b>Alibi breaks:</b> {c.reason}
          <span className="srcs"> [{(c.sources || []).join(", ")}]</span></p>
      ))}
      {note && <p className="note">{note}</p>}

      <div className="graph-wrap">
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          nodeLabel={(n) => `${n.label} (${n.type})`}
          nodeColor={(n) => COLORS[n.type] || "#aaa"}
          nodeRelSize={6}
          linkLabel={(l) => l.relation}
          linkColor={(l) => (l._c ? "#ff2d2d" : "rgba(255,255,255,0.22)")}
          linkWidth={(l) => (l._c ? 3 : 1)}
          linkDirectionalParticles={(l) => (l._c ? 4 : 1)}
          linkDirectionalParticleWidth={(l) => (l._c ? 4 : 2)}
          linkDirectionalParticleColor={(l) => (l._c ? "#ff5252" : "#888")}
        />
      </div>
      <div className="legend">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k}><i style={{ background: c }} /> {k}</span>
        ))}
        <span><i style={{ background: "#ff2d2d" }} /> contradiction</span>
      </div>
    </div>
  );
}
