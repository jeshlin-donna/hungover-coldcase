import { useEffect, useState } from "react";
import { api } from "./api.js";
import GraphPanel from "./components/GraphPanel.jsx";
import ComparePanel from "./components/ComparePanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";

const TABS = [
  { id: "graph", label: "Case Graph" },
  { id: "compare", label: "Graph vs Vector" },
  { id: "timeline", label: "Timeline" },
];

export default function App() {
  const [tab, setTab] = useState("compare");
  const [mode, setMode] = useState(null); // backend mode: live | degraded

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("offline"));
  }, []);

  return (
    <div className="app">
      <header>
        <div>
          <h1>HungOver · Cold Case Connector</h1>
          <p className="tag">Every detective had a piece of the evidence. Nobody had the
            shared memory to connect it. Cognee does.</p>
        </div>
        <span className={`badge ${mode}`}>backend: {mode || "…"}</span>
      </header>

      <nav>
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? "active" : ""}
                  onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </nav>

      <main>
        {tab === "graph" && <GraphPanel />}
        {tab === "compare" && <ComparePanel />}
        {tab === "timeline" && <TimelinePanel />}
      </main>

      <footer>Synthetic data only · illustrative demo, not an operational tool.</footer>
    </div>
  );
}
