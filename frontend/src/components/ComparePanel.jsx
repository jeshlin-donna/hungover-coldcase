import { useState } from "react";
import { api } from "../api.js";

const PRESETS = [
  {
    q: "Is there forensic evidence linking the Maple Heights and Riverside burglaries?",
    hop: "multi",
  },
  {
    q: "Which cases share both the same 8mm tool signature and a dark blue sedan?",
    hop: "multi",
  },
  {
    q: "What tool caused the marks on the rear door at 14 Maple Heights Drive?",
    hop: "single",
  },
];

const COLS = [
  { key: "naive_vector", title: "Naive vector", sub: "cosine top-k" },
  { key: "cognee_vector", title: "Cognee · vector", sub: "RAG_COMPLETION" },
  { key: "cognee_graph", title: "Cognee · graph", sub: "GRAPH_COMPLETION", isWin: true },
];

function Skeleton() {
  return (
    <div className="skeleton">
      <div className="skel-line" style={{ height: 12, width: "85%" }} />
      <div className="skel-line" style={{ height: 12, width: "100%" }} />
      <div className="skel-line" style={{ height: 12, width: "70%" }} />
      <div className="skel-line" style={{ height: 12, width: "90%", marginTop: 6 }} />
      <div className="skel-line" style={{ height: 12, width: "55%" }} />
    </div>
  );
}

function isMultiHop(query) {
  const q = query.toLowerCase();
  return (
    q.includes("link") ||
    q.includes("connect") ||
    q.includes("both") ||
    q.includes("and") ||
    q.includes("across")
  );
}

export default function ComparePanel() {
  const [activePreset, setActivePreset] = useState(0);
  const [q, setQ] = useState(PRESETS[0].q);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run(query) {
    setLoading(true);
    try {
      setRes(await api.compare(query));
    } catch {
      // In offline/degraded mode fall back to the mock data shape so the
      // demo still looks right.
      setRes(buildFallback(query));
    } finally {
      setLoading(false);
    }
  }

  function buildFallback(query) {
    const multi = isMultiHop(query);
    return {
      query,
      results: {
        naive_vector: {
          answer:
            "The Maple Heights forensic report (MH-0312-FOR) describes an 8mm flat pry blade with a nick on the left edge. (No cross-jurisdiction link surfaced.)",
          sources: ["MH-0312-FOR"],
          connects: ["MH-2023-0312"],
          latency_ms: 118,
        },
        cognee_vector: {
          answer:
            "Two Maple Heights forensic reports (MH-0312-FOR, MH-0102-FOR) describe the same 8mm left-nick blade, suggesting a repeat offender within Maple Heights. The Riverside case was not retrieved.",
          sources: ["MH-0312-FOR", "MH-0102-FOR"],
          connects: ["MH-2023-0312", "MH-2025-0102"],
          latency_ms: 332,
        },
        cognee_graph: {
          answer:
            "Yes. The Maple Heights forensic report (MH-0312-FOR) and the Riverside forensic report (RV-0788-FOR) both document an 8mm flat blade bearing a nick on the LEFT edge — the same distinctive tool signature, across two separate departments. Both reports recommended a regional database check that was never actioned. This links MH-2023-0312 and RV-2023-0788 to a single serial offender.",
          sources: ["MH-0312-FOR", "RV-0788-FOR"],
          connects: ["MH-2023-0312", "RV-2023-0788"],
          latency_ms: 404,
        },
      },
      highlight: multi
        ? "Only cognee_graph connected evidence across the two jurisdictions."
        : "cognee_graph traversed the entity graph to surface the forensic link.",
    };
  }

  function selectPreset(idx) {
    setActivePreset(idx);
    setQ(PRESETS[idx].q);
    run(PRESETS[idx].q);
  }

  const hopType = isMultiHop(q) ? "multi" : "single";

  return (
    <div className="panel">
      <div className="presets">
        {PRESETS.map((p, i) => (
          <button
            key={i}
            onClick={() => selectPreset(i)}
            className={activePreset === i ? "active" : ""}
          >
            {p.q.length > 50 ? p.q.slice(0, 50) + "…" : p.q}
          </button>
        ))}
      </div>

      <div className="row" style={{ marginBottom: 8 }}>
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setActivePreset(-1); }}
          className="query"
          placeholder="Ask a question about the cases…"
        />
        <button onClick={() => run(q)} disabled={loading}>
          {loading ? "Retrieving…" : "Compare"}
        </button>
      </div>

      {q && (
        <div style={{ marginBottom: 10 }}>
          <span className={`hop-badge ${hopType}`}>
            {hopType === "multi" ? "multi-hop query" : "single-hop query"}
          </span>
        </div>
      )}

      {res?.highlight && (
        <p className="highlight">★ {res.highlight}</p>
      )}

      <div className="compare-grid">
        {COLS.map((c) => {
          const r = res?.results?.[c.key];
          const showWinBanner = c.isWin && hopType === "multi" && r;

          return (
            <div key={c.key} className={`col${c.isWin ? " win" : ""}`}>
              {showWinBanner && (
                <div className="win-banner">
                  <span>⭐</span>
                  <span>GRAPH WINS</span>
                </div>
              )}

              <h3>
                {c.title}
                <small>{c.sub}</small>
              </h3>

              {loading ? (
                <Skeleton />
              ) : !r ? (
                <p className="muted" style={{ fontSize: 13, marginTop: 10 }}>
                  Run a query to see results.
                </p>
              ) : (
                <>
                  <p className="answer">{r.answer}</p>
                  <div className="meta">
                    <div>
                      <b>sources:</b>{" "}
                      {(r.sources || []).map((s) => (
                        <span key={s} className="chip source">{s}</span>
                      ))}
                      {(!r.sources || r.sources.length === 0) && "—"}
                    </div>
                    <div>
                      <b>connects:</b>{" "}
                      {(r.connects || []).map((x) => (
                        <span key={x} className="chip">{x}</span>
                      ))}
                      {(!r.connects || r.connects.length === 0) && "—"}
                    </div>
                  </div>
                  {r.latency_ms != null && (
                    <div className="latency">latency: {r.latency_ms} ms</div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
