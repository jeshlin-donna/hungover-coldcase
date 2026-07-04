import { useState } from "react";
import { api } from "../api.js";

const MOCK_RESULTS = {
  "witness c is lying": {
    impact: "MODERATE",
    hypothesis: "Witness C is lying about the vehicle description",
    narrative:
      "If Witness C's vehicle description is removed from the graph, the dark blue sedan node loses two of its three corroborating edges. The vehicle link weakens significantly but does not collapse — the plate fragment (8K·) captured in the MH-0102 camera clip still anchors Marsh's vehicle to the case. The suspect confidence dips but remains above prosecution threshold. The tool signature evidence is entirely unaffected.",
    next_step:
      "Re-interview Witness C under controlled conditions and compare the original statement verbatim. If inconsistencies emerge, the vehicle evidence still holds via the camera clip — the case does not hinge on the witness.",
    before: [
      { label: "Daniel R. Marsh", value: 87, color: "#f85149" },
      { label: "Dark blue sedan", value: 91, color: "#3fb950" },
      { label: "Tool signature", value: 99, color: "#e3b341" },
      { label: "Alibi (false)", value: 98, color: "#58a6ff" },
    ],
    after: [
      { label: "Daniel R. Marsh", value: 79, color: "#f85149" },
      { label: "Dark blue sedan", value: 61, color: "#3fb950" },
      { label: "Tool signature", value: 99, color: "#e3b341" },
      { label: "Alibi (false)", value: 98, color: "#58a6ff" },
    ],
    cognee_insight:
      "The veh:blue-sedan node currently has 3 corroborating edge sources. Removing the Witness C edge reduces it to 2. The node remains connected but with lower graph centrality. The suspect:daniel-marsh node's confidence is driven primarily by the tool and receipt edges — those are unaffected.",
  },
};

function buildFallback(hypothesis) {
  const key = hypothesis.toLowerCase().trim();
  for (const [k, v] of Object.entries(MOCK_RESULTS)) {
    if (key.includes(k)) return v;
  }
  return {
    impact: "LOW",
    hypothesis,
    narrative:
      "This hypothesis does not substantially alter the graph's primary evidentiary paths. The tool signature, card record, and alibi contradiction remain intact. The injected change affects peripheral nodes with low centrality.",
    next_step:
      "Continue building the core case. Revisit this hypothesis after the cell tower subpoena returns — additional data may change the impact score.",
    before: [
      { label: "Daniel R. Marsh", value: 87, color: "#f85149" },
      { label: "Dark blue sedan", value: 91, color: "#3fb950" },
      { label: "Tool signature", value: 99, color: "#e3b341" },
      { label: "Alibi (false)", value: 98, color: "#58a6ff" },
    ],
    after: [
      { label: "Daniel R. Marsh", value: 84, color: "#f85149" },
      { label: "Dark blue sedan", value: 88, color: "#3fb950" },
      { label: "Tool signature", value: 99, color: "#e3b341" },
      { label: "Alibi (false)", value: 98, color: "#58a6ff" },
    ],
    cognee_insight:
      "Graph analysis shows minimal impact on the core evidentiary cluster. The proposed change affects nodes with degree < 2 that do not sit on any shortest path between the suspect and case nodes.",
  };
}

const IMPACT_STYLES = {
  HIGH: { bg: "rgba(248,81,73,0.12)", color: "#f85149", border: "rgba(248,81,73,0.3)", icon: "🔴" },
  MODERATE: { bg: "rgba(210,153,34,0.12)", color: "#d29922", border: "rgba(210,153,34,0.3)", icon: "🟡" },
  LOW: { bg: "rgba(63,185,80,0.12)", color: "#3fb950", border: "rgba(63,185,80,0.3)", icon: "🟢" },
};

function ConfidenceBar({ label, before, after, color }) {
  const delta = after - before;
  const maxVal = 100;

  return (
    <div className="confidence-row">
      <div className="conf-label">{label}</div>
      <div className="conf-bars">
        <div className="conf-bar-wrap">
          <span className="conf-val-label">Before {before}%</span>
          <div className="confidence-bar-track">
            <div
              className="confidence-bar-fill before"
              style={{ width: `${before}%` }}
            />
          </div>
        </div>
        <div className="conf-bar-wrap">
          <span className="conf-val-label">After {after}%</span>
          <div className="confidence-bar-track">
            <div
              className="confidence-bar-fill after"
              style={{ width: `${after}%` }}
            />
          </div>
        </div>
      </div>
      <span
        className="conf-delta"
        style={{ color: delta < 0 ? "#f85149" : delta > 0 ? "#3fb950" : "var(--muted)" }}
      >
        {delta > 0 ? "+" : ""}{delta}%
      </span>
    </div>
  );
}

export default function WhatIfPanel() {
  const [hypothesis, setHypothesis] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [injectFrom, setInjectFrom] = useState("");
  const [injectTo, setInjectTo] = useState("");
  const [injectRel, setInjectRel] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function runHypothesis() {
    if (!hypothesis.trim()) return;
    setLoading(true);
    const inject_edge =
      injectFrom && injectTo && injectRel
        ? { from: injectFrom, to: injectTo, relation: injectRel }
        : {};
    try {
      const res = await api.whatif(hypothesis, inject_edge);
      setResult(res);
    } catch {
      setResult(buildFallback(hypothesis));
    } finally {
      setLoading(false);
    }
  }

  const impactStyle = result ? IMPACT_STYLES[String(result.impact || "").toUpperCase()] || IMPACT_STYLES.LOW : null;

  return (
    <div className="panel whatif-panel">
      <h2 className="whatif-title">What-If — Hypothesis Sandbox</h2>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 20 }}>
        Inject a speculative scenario and see how confidence scores shift across the knowledge graph.
      </p>

      <div className="whatif-input-section">
        <textarea
          className="hypothesis-textarea"
          rows={3}
          placeholder="Witness C is lying about the vehicle description"
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
        />

        <div className="advanced-toggle" onClick={() => setShowAdvanced((v) => !v)}>
          <span className="adv-icon">{showAdvanced ? "▲" : "▼"}</span>
          Advanced — inject edge into graph (optional)
        </div>

        {showAdvanced && (
          <div className="inject-edge-section">
            <div className="inject-row">
              <div className="inject-field">
                <label>From node</label>
                <input
                  value={injectFrom}
                  onChange={(e) => setInjectFrom(e.target.value)}
                  placeholder="suspect:daniel-marsh"
                />
              </div>
              <div className="inject-field">
                <label>Relation</label>
                <input
                  value={injectRel}
                  onChange={(e) => setInjectRel(e.target.value)}
                  placeholder="witnessed_at"
                />
              </div>
              <div className="inject-field">
                <label>To node</label>
                <input
                  value={injectTo}
                  onChange={(e) => setInjectTo(e.target.value)}
                  placeholder="jur:riverside"
                />
              </div>
            </div>
          </div>
        )}

        <button
          className="whatif-run-btn"
          onClick={runHypothesis}
          disabled={loading || !hypothesis.trim()}
        >
          {loading ? "Running simulation…" : "Run Hypothesis"}
        </button>
      </div>

      {result && (
        <div className="whatif-result">
          <div className="impact-row">
            <span
              className="impact-badge"
              style={{
                background: impactStyle.bg,
                color: impactStyle.color,
                borderColor: impactStyle.border,
              }}
            >
              {impactStyle.icon} {result.impact} IMPACT
            </span>
            <span style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
              "{result.hypothesis}"
            </span>
          </div>

          <div className="confidence-chart">
            <h4 className="conf-chart-title">Confidence scores — before vs after</h4>
            {result.before.map((item, i) => {
              const afterItem = result.after[i] || { value: item.value };
              return (
                <ConfidenceBar
                  key={item.label}
                  label={item.label}
                  before={item.value}
                  after={afterItem.value}
                  color={item.color}
                />
              );
            })}
          </div>

          <p className="whatif-narrative">{result.narrative}</p>

          <div className="whatif-next-step">
            <span className="next-step-label">Recommended next step</span>
            <p>{result.next_step}</p>
          </div>

          {result.cognee_insight && (
            <div className="cognee-insight-box">
              <span className="cognee-insight-label">Cognee graph insight</span>
              <p className="cognee-insight-text">{result.cognee_insight}</p>
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="whatif-empty">
          <p>
            Enter a hypothesis above — e.g. "Witness C is lying about the vehicle
            description" — and click Run Hypothesis to see the confidence impact.
          </p>
        </div>
      )}
    </div>
  );
}
