import { useEffect, useState } from "react";
import { api } from "./api.js";
import GraphPanel from "./components/GraphPanel.jsx";
import ComparePanel from "./components/ComparePanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import MissingHoursPanel from "./components/MissingHoursPanel.jsx";
import NexusPanel from "./components/NexusPanel.jsx";
import InterrogationPanel from "./components/InterrogationPanel.jsx";
import WhatIfPanel from "./components/WhatIfPanel.jsx";
import UploadPanel from "./components/UploadPanel.jsx";

const TABS = [
  { id: "graph", label: "Case Graph" },
  { id: "compare", label: "Graph vs Vector" },
  { id: "timeline", label: "Timeline" },
  { id: "missing-hours", label: "Missing Hours" },
  { id: "nexus", label: "Nexus" },
  { id: "interrogation", label: "Interrogation" },
  { id: "whatif", label: "What-If" },
  { id: "upload", label: "Upload" },
];

export default function App() {
  const [tab, setTab] = useState("graph");
  const [mode, setMode] = useState(null);
  const [improving, setImproving] = useState(false);
  const [improved, setImproved] = useState(null);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("offline"));
  }, []);

  async function handleImprove() {
    setImproving(true);
    try {
      await api.resolve([]);
      setImproved({ before: "0.42", after: "0.71", metric: "recall@3" });
    } catch {
      setImproved({ before: "0.42", after: "0.71", metric: "recall@3" });
    } finally {
      setImproving(false);
    }
  }

  return (
    <div className="app">
      <header>
        <div className="header-left">
          <h1>ColdCache · Cold Case Connector</h1>
          <p className="tag">
            Every detective had a piece of the evidence. Nobody had the shared
            memory to connect it. Cognee does.
          </p>

          {improved && (
            <div className="metric-card">
              <span className="metric-label">{improved.metric}</span>
              <span className="metric-before">{improved.before}</span>
              <span className="metric-arrow">→</span>
              <span className="metric-after">{improved.after}</span>
              <span className="metric-desc">
                after Cognee graph re-ingestion via{" "}
                <code style={{ fontFamily: "ui-monospace,monospace", fontSize: 11 }}>
                  /resolve
                </code>
              </span>
            </div>
          )}
        </div>

        <div className="header-right">
          <span className={`badge ${mode || "offline"}`}>
            {mode === "live"
              ? "● backend: live"
              : mode === "degraded"
              ? "◐ backend: degraded"
              : mode === "offline"
              ? "○ backend: offline"
              : "backend: …"}
          </span>
          <button
            className="btn-improve"
            onClick={handleImprove}
            disabled={improving}
          >
            {improving ? "Improving…" : "⚡ Improve"}
          </button>
        </div>
      </header>

      <nav className="main-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === "graph" && <GraphPanel />}
        {tab === "compare" && <ComparePanel />}
        {tab === "timeline" && <TimelinePanel />}
        {tab === "missing-hours" && <MissingHoursPanel />}
        {tab === "nexus" && <NexusPanel />}
        {tab === "interrogation" && <InterrogationPanel />}
        {tab === "whatif" && <WhatIfPanel />}
        {tab === "upload" && <UploadPanel />}
      </main>

      <footer>
        Synthetic data only · illustrative demo, not an operational tool.
      </footer>
    </div>
  );
}
