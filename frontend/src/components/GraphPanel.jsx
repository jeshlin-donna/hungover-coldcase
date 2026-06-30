import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api.js";

const COLORS = {
  case: "#ff6b6b", tool: "#ffd93d", vehicle: "#6bcB77", mo: "#4d96ff",
  suspect: "#c77dff", jurisdiction: "#8d99ae",
};

export default function GraphPanel() {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [note, setNote] = useState("");
  const fgRef = useRef();

  function toGraph(g) {
    return {
      nodes: g.nodes.map((n) => ({ ...n })),
      links: g.edges.map((e) => ({ source: e.source, target: e.target, relation: e.relation })),
    };
  }

  useEffect(() => { api.graph().then((g) => setData(toGraph(g))); }, []);

  async function expunge() {
    const res = await api.expunge("case:RV-0788");
    setData(toGraph(res.graph));
    setNote(`forget(): removed ${res.removed.join(", ") || "the sealed subgraph"} — rest intact.`);
  }

  return (
    <div className="panel">
      <div className="row">
        <p>The case web. Tool signature, vehicle, and MO bridge two jurisdictions that
          never shared a database.</p>
        <button className="danger" onClick={expunge}>Expunge Riverside record (forget)</button>
      </div>
      {note && <p className="note">{note}</p>}
      <div className="graph-wrap">
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          nodeLabel={(n) => `${n.label} (${n.type})`}
          nodeColor={(n) => COLORS[n.type] || "#aaa"}
          nodeRelSize={6}
          linkLabel={(l) => l.relation}
          linkColor={() => "rgba(255,255,255,0.25)"}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={2}
        />
      </div>
      <div className="legend">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k}><i style={{ background: c }} /> {k}</span>
        ))}
      </div>
    </div>
  );
}
