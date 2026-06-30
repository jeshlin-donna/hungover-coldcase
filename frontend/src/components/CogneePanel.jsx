import { useState } from "react";
import { api } from "../api.js";

const API_CARDS = [
  {
    id: "remember",
    name: "remember()",
    color: "var(--accent)",
    icon: "💾",
    tagline: "Ingest siloed evidence into one persistent knowledge graph",
    description:
      "Calls cognee.add() + cognee.cognify(). Takes raw text, extracts entities and relationships, and builds them into the graph. Used for every case file, forensic report, and witness statement in the corpus.",
    code: `await cognee.add(text, dataset_name=dataset)\nawait cognee.cognify(datasets=[dataset])`,
    tryLabel: "Ingest test document",
    tryMode: "remember",
  },
  {
    id: "recall",
    name: "recall()",
    color: "var(--win)",
    icon: "🔍",
    tagline: "Query with GRAPH, VECTOR, or TRIPLET search modes",
    description:
      "Three search types, same query: GRAPH_COMPLETION for entity traversal, RAG_COMPLETION for vector RAG, TRIPLET_COMPLETION for raw relationship extraction (alibi check). The benchmark compares all three.",
    code: `await cognee.search(\n  query_text=query,\n  query_type=SearchType.GRAPH_COMPLETION,\n  datasets=[dataset]\n)`,
    tryLabel: "Recall cross-jurisdiction link",
    tryMode: "recall",
    tryQuery:
      "Which suspect appears in both the Millbrook Heights and Riverside View burglaries?",
  },
  {
    id: "improve",
    name: "improve()",
    color: "var(--warning)",
    icon: "⚡",
    tagline: "Merge detective session hunches into permanent graph memory",
    description:
      "Hunches logged mid-case (with session_id) stay in ephemeral memory. On case resolution, improve() bridges them into the permanent graph and re-weights connections. The graph gets sharper as the investigation progresses.",
    code: `# Log hunch (session memory only)\nawait cognee.remember(text, session_id=sid)\n\n# On resolution: merge into permanent graph\nawait cognee.improve(dataset=dataset, session_ids=sids)`,
    tryLabel: "Run improve() on case",
    tryMode: "improve",
  },
  {
    id: "forget",
    name: "forget()",
    color: "var(--danger)",
    icon: "🗑️",
    tagline: "Legal record expungement — surgical subgraph deletion",
    description:
      "After a sentence is served, a court can order a record sealed. forget() removes that dataset's subgraph surgically — every other node and edge intact. Real legal use case, not a demo cleanup function.",
    code: `await cognee.forget(dataset=dataset)\n# Every other node/edge in the graph: untouched`,
    tryLabel: "Expunge sealed record",
    tryMode: "forget",
  },
];

function useCardState() {
  const [loading, setLoading] = useState({});
  const [result, setResult] = useState({});
  const [error, setError] = useState({});
  const [showConfirm, setShowConfirm] = useState(false);

  function setCardLoading(id, val) {
    setLoading((s) => ({ ...s, [id]: val }));
  }
  function setCardResult(id, val) {
    setResult((s) => ({ ...s, [id]: val }));
  }
  function setCardError(id, val) {
    setError((s) => ({ ...s, [id]: val }));
  }

  return {
    loading,
    result,
    error,
    showConfirm,
    setShowConfirm,
    setCardLoading,
    setCardResult,
    setCardError,
  };
}

function StatusDot({ id }) {
  // In a real app this would pull from a health check.
  // For demo purposes, show green for all APIs.
  return (
    <span
      title="API live"
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: "var(--win)",
        marginRight: 6,
        boxShadow: "0 0 4px var(--win)",
      }}
    />
  );
}

function ApiCard({ card, state }) {
  const {
    loading,
    result,
    error,
    showConfirm,
    setShowConfirm,
    setCardLoading,
    setCardResult,
    setCardError,
  } = state;

  const isLoading = loading[card.id];
  const cardResult = result[card.id];
  const cardError = error[card.id];

  async function handleTry() {
    if (card.tryMode === "forget") {
      setShowConfirm(true);
      return;
    }
    if (card.tryMode === "remember") {
      // No live call — point to Messy Desk
      setCardResult(card.id, "__remember__");
      return;
    }
    if (card.tryMode === "recall") {
      setCardLoading(card.id, true);
      setCardError(card.id, null);
      setCardResult(card.id, null);
      try {
        const res = await api.recall(card.tryQuery, "GRAPH");
        const text =
          typeof res === "string"
            ? res
            : res?.answer || res?.result || JSON.stringify(res, null, 2);
        setCardResult(card.id, text);
      } catch (e) {
        setCardError(
          card.id,
          e?.message || "Backend offline — start the server to try live recall."
        );
      } finally {
        setCardLoading(card.id, false);
      }
      return;
    }
    if (card.tryMode === "improve") {
      setCardLoading(card.id, true);
      setCardError(card.id, null);
      setCardResult(card.id, null);
      try {
        await api.resolve([]);
        setCardResult(card.id, "Session hunches merged into permanent graph.");
      } catch (e) {
        setCardError(
          card.id,
          e?.message || "Backend offline — start the server to try improve()."
        );
      } finally {
        setCardLoading(card.id, false);
      }
      return;
    }
  }

  async function handleConfirmForget() {
    setShowConfirm(false);
    setCardLoading(card.id, true);
    setCardError(card.id, null);
    setCardResult(card.id, null);
    try {
      await api.expunge("marsh_record");
      setCardResult(
        card.id,
        "marsh_record subgraph removed. All other nodes and edges untouched."
      );
    } catch (e) {
      setCardError(
        card.id,
        e?.message || "Backend offline — start the server to try forget()."
      );
    } finally {
      setCardLoading(card.id, false);
    }
  }

  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 20,
        position: "relative",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {/* Top accent line */}
      <div
        style={{
          height: 3,
          width: 40,
          background: card.color,
          borderRadius: 2,
          marginBottom: 2,
        }}
      />

      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 22 }}>{card.icon}</span>
        <span
          style={{
            fontFamily: '"JetBrains Mono", "Fira Mono", monospace',
            color: card.color,
            fontSize: 20,
            fontWeight: 600,
          }}
        >
          {card.name}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center" }}>
          <StatusDot id={card.id} />
          <span style={{ fontSize: 11, color: "var(--muted)" }}>live</span>
        </span>
      </div>

      {/* Tagline */}
      <div style={{ color: "var(--text)", fontSize: 13, fontWeight: 500 }}>
        {card.tagline}
      </div>

      {/* Description */}
      <div style={{ color: "var(--text-2)", fontSize: 12, lineHeight: 1.6 }}>
        {card.description}
      </div>

      {/* Code block */}
      <pre
        style={{
          background: "var(--bg)",
          borderRadius: 8,
          padding: 12,
          fontFamily: '"JetBrains Mono", "Fira Mono", monospace',
          fontSize: 12,
          color: "var(--text-2)",
          borderLeft: `3px solid ${card.color}`,
          margin: 0,
          overflowX: "auto",
          whiteSpace: "pre",
        }}
      >
        {card.code}
      </pre>

      {/* Try button */}
      <button
        onClick={handleTry}
        disabled={isLoading}
        style={{
          background: "transparent",
          border: `1px solid ${card.color}`,
          color: card.color,
          borderRadius: 6,
          padding: "8px 16px",
          cursor: isLoading ? "wait" : "pointer",
          fontSize: 12,
          fontFamily: "inherit",
          opacity: isLoading ? 0.7 : 1,
          alignSelf: "flex-start",
          transition: "opacity 0.2s",
        }}
      >
        {isLoading ? "Running…" : card.tryLabel}
      </button>

      {/* Forget confirmation modal */}
      {card.tryMode === "forget" && showConfirm && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0,0,0,0.82)",
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 16,
            zIndex: 10,
            padding: 24,
          }}
        >
          <div style={{ color: "var(--danger)", fontWeight: 700, fontSize: 15, textAlign: "center" }}>
            Expunge marsh_record?
          </div>
          <div style={{ color: "var(--text-2)", fontSize: 12, textAlign: "center" }}>
            This will call <code style={{ fontFamily: "monospace" }}>forget(dataset="marsh_record")</code> and surgically remove that subgraph. All other graph data remains untouched.
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleConfirmForget}
              style={{
                background: "transparent",
                border: "1px solid var(--danger)",
                color: "var(--danger)",
                borderRadius: 6,
                padding: "7px 18px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Confirm expunge
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--muted)",
                borderRadius: 6,
                padding: "7px 18px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Live result area */}
      {(cardResult || cardError) && (
        <div
          style={{
            marginTop: 4,
            background: "var(--bg)",
            borderRadius: 8,
            padding: 12,
            borderLeft: `3px solid ${cardError ? "var(--danger)" : card.color}`,
          }}
        >
          {cardResult === "__remember__" ? (
            <div style={{ color: "var(--text-2)", fontSize: 12, lineHeight: 1.6 }}>
              Ingest is triggered via the{" "}
              <strong style={{ color: "var(--text)" }}>Messy Desk</strong> panel (tab 9) — drag a file there to call{" "}
              <code style={{ fontFamily: "monospace" }}>remember()</code> live.
            </div>
          ) : cardError ? (
            <div style={{ color: "var(--danger)", fontSize: 12 }}>{cardError}</div>
          ) : (
            <div
              style={{
                color: "var(--text)",
                fontSize: 12,
                fontFamily: '"JetBrains Mono", monospace',
                whiteSpace: "pre-wrap",
                lineHeight: 1.6,
              }}
            >
              {cardResult}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CogneePanel() {
  // Each card manages its own state; forget confirmation is shared per card instance.
  // We use separate state instances per card via the hook below.
  const states = [
    useCardState(),
    useCardState(),
    useCardState(),
    useCardState(),
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      {/* Header */}
      <div className="section-header">
        <div className="section-title">Cognee Memory Engine</div>
        <div className="section-subtitle">
          All 4 lifecycle APIs — each mapped to a real investigative need
        </div>
      </div>

      {/* 4 API cards — 2-column grid on wide screens, 1-column on narrow */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: 20,
        }}
      >
        {API_CARDS.map((card, i) => (
          <ApiCard key={card.id} card={card} state={states[i]} />
        ))}
      </div>

      {/* Architecture diagram */}
      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 24,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text)",
            marginBottom: 16,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}
        >
          Cognee Architecture in ColdCache
        </div>
        <pre
          style={{
            fontFamily: '"JetBrains Mono", "Fira Mono", monospace',
            fontSize: 12,
            color: "var(--text-2)",
            lineHeight: 2,
            margin: 0,
            overflowX: "auto",
          }}
        >
{`[Case Files]   → remember()  → [Knowledge Graph]  → recall(GRAPH) → [Investigator]
[Hunches]      → improve()   → [Graph Update]     → recall(GRAPH) → [Sharper Results]
[Court Order]  → forget()    → [Subgraph Removed] → recall(GRAPH) → [Clean Results]`}
        </pre>

        {/* Stats row */}
        <div
          style={{
            marginTop: 20,
            paddingTop: 16,
            borderTop: "1px solid var(--border)",
            display: "flex",
            gap: 24,
            flexWrap: "wrap",
          }}
        >
          {[
            { val: "261", label: "docs ingested" },
            { val: "3", label: "datasets" },
            { val: "4", label: "APIs" },
            { val: "47", label: "graph nodes" },
          ].map(({ val, label }) => (
            <div key={label} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span
                style={{
                  fontFamily: '"JetBrains Mono", monospace',
                  fontSize: 22,
                  fontWeight: 700,
                  color: "var(--accent)",
                }}
              >
                {val}
              </span>
              <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
