import { useState } from "react";
import { api } from "../api.js";

const PRESETS = [
  "Is there forensic evidence linking the Maple Heights and Riverside burglaries?",
  "Which cases share both the same 8mm tool signature and a dark blue sedan?",
  "What tool caused the marks on the rear door at 14 Maple Heights Drive?",
];

const COLS = [
  { key: "naive_vector", title: "Naive vector", sub: "cosine top-k" },
  { key: "cognee_vector", title: "Cognee · vector", sub: "RAG_COMPLETION" },
  { key: "cognee_graph", title: "Cognee · graph", sub: "GRAPH_COMPLETION" },
];

export default function ComparePanel() {
  const [q, setQ] = useState(PRESETS[0]);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run(query) {
    setQ(query);
    setLoading(true);
    try { setRes(await api.compare(query)); }
    finally { setLoading(false); }
  }

  return (
    <div className="panel">
      <div className="presets">
        {PRESETS.map((p) => (
          <button key={p} onClick={() => run(p)} className={p === q ? "active" : ""}>
            {p.length > 46 ? p.slice(0, 46) + "…" : p}
          </button>
        ))}
      </div>
      <div className="row">
        <input value={q} onChange={(e) => setQ(e.target.value)} className="query" />
        <button onClick={() => run(q)} disabled={loading}>
          {loading ? "Retrieving…" : "Compare"}
        </button>
      </div>

      {res?.highlight && <p className="highlight">★ {res.highlight}</p>}

      <div className="compare-grid">
        {COLS.map((c) => {
          const r = res?.results?.[c.key];
          return (
            <div key={c.key} className={`col ${c.key === "cognee_graph" ? "win" : ""}`}>
              <h3>{c.title} <small>{c.sub}</small></h3>
              {!r ? <p className="muted">—</p> : (
                <>
                  <p className="answer">{r.answer}</p>
                  <div className="meta">
                    <div><b>sources:</b> {r.sources?.join(", ") || "—"}</div>
                    <div><b>connects:</b> {(r.connects || []).map((x) => (
                      <span key={x} className="chip">{x}</span>
                    ))}</div>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
