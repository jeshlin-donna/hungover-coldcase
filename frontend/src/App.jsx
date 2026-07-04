import { useEffect, useState } from "react";
import { api } from "./api.js";
import ChatPanel from "./components/ChatPanel.jsx";
import GraphPanel from "./components/GraphPanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import InterrogationPanel from "./components/InterrogationPanel.jsx";
import WhatIfPanel from "./components/WhatIfPanel.jsx";
import CaseHome from "./components/CaseHome.jsx";
import CaseImportPanel from "./components/CaseImportPanel.jsx";
import SuspectTimelinePanel from "./components/SuspectTimelinePanel.jsx";

const MAIN_TABS = [
  {
    id: "upload",
    label: "Import Case Files and Data",
    icon: "📁",
    blurb: "Drag-and-drop ingestion for new case files (audio, photos, text) straight into the knowledge graph.",
    tryText: "Try: drop a file and watch it get parsed into graph nodes in real time.",
  },
];

const CHAT_TAB = {
  id: "chat",
  label: "Case Chat",
  icon: "💬",
  blurb: "Ask plain-English questions about the case; answers are sourced live from the knowledge graph.",
  tryText: "Try: \"Who appears across both Millbrook and Riverside cases?\"",
};

const SUB_TABS = [
  {
    id: "graph",
    label: "Evidence Board",
    icon: "🕸️",
    blurb: "The interactive case graph — people, places, tools, and evidence as connected nodes.",
    tryText: "Try: drag the temporal slider, then click \"Run alibi check\" to see the contradiction light up.",
  },
  {
    id: "timeline",
    label: "Timeline",
    icon: "📅",
    blurb: "Chronological case view with missing-hour detection and suspect movement reconstruction in one place.",
    tryText: "Try: replay the case, inspect timeline gaps, and review suspect movements together.",
  },
  {
    id: "interrogation",
    label: "Interrogation",
    icon: "🎯",
    blurb: "Generates tactical questions for a suspect, built from contradictions between their statements and hard evidence.",
    tryText: "Try: generate a question that traps the suspect's alibi claim.",
  },
  {
    id: "whatif",
    label: "What-If",
    icon: "🤔",
    blurb: "A safe sandbox to test hypotheses (e.g. \"what if this witness is unreliable?\") without touching real data.",
    tryText: "Try: zero out a witness's reliability score and see how the case's alibi integrity changes.",
  },
];

const NAV_TABS = SUB_TABS;
const GUIDE_TABS = [MAIN_TABS[0], ...SUB_TABS, CHAT_TAB];

const GUIDE_SEEN_KEY = "coldcache_guide_seen";

export default function App() {
  const [activeCase, setActiveCase] = useState(null);
  const [tab, setTab] = useState("upload");
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [mode, setMode] = useState(null);
  const [stats, setStats] = useState({ nodes: 0, docs: 0, jurisdictions: 0, alibiBreak: false });
  const [improving, setImproving] = useState(false);
  const [improved, setImproved] = useState(null);
  const [justImproved, setJustImproved] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [toast, setToast] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [showGuide, setShowGuide] = useState(() => {
    try {
      return !localStorage.getItem(GUIDE_SEEN_KEY);
    } catch {
      return true;
    }
  });

  function closeGuide() {
    setShowGuide(false);
    try {
      localStorage.setItem(GUIDE_SEEN_KEY, "1");
    } catch {
      // ignore (private browsing etc.)
    }
  }

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("offline"));
    if (!activeCase) return;
    api.caseStats(activeCase.id).then((s) => setStats({
      nodes: s.nodes, docs: s.docs, jurisdictions: s.jurisdictions, alibiBreak: s.alibi_break,
    })).catch(() => {});
  }, [activeCase]);

  useEffect(() => {
    function onKey(e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      const idx = parseInt(e.key, 10) - 1;
      if (idx === 0) {
        setWorkspaceOpen(false);
        setTab("upload");
      } else if (idx > 0 && idx <= SUB_TABS.length) {
        setWorkspaceOpen(true);
        setTab(SUB_TABS[idx - 1].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  }

  async function handleImprove() {
    setImproving(true);
    try {
      const result = await api.resolve([]);
      setImproved({ before: Number(result.before).toFixed(2), after: Number(result.after).toFixed(2), metric: result.metric });
      setJustImproved(true);
      // Re-fetch graph
      try {
        const g = await api.graph();
        setGraphData(g);
      } catch {
        // Keep existing graph
      }
      setTimeout(() => setJustImproved(false), 3000);
    } catch {
      showToast("Could not improve the case graph. Check the backend connection.");
    } finally {
      setImproving(false);
    }
  }

  async function handleExportReport() {
    setShowReport(true);
    if (report) return; // already loaded
    setReportLoading(true);
    try {
      const r = await api.report();
      setReport(r);
    } catch {
      setReport(null);
    } finally {
      setReportLoading(false);
    }
  }

  function handleGraphUpdated() {
    api.caseStats(activeCase.id).then((s) => setStats({
      nodes: s.nodes, docs: s.docs, jurisdictions: s.jurisdictions, alibiBreak: s.alibi_break,
    })).catch(() => {});
    api.graph(activeCase.id).then((g) => {
      const prevCount = graphData?.nodes?.length || 0;
      const newCount = g?.nodes?.length || 0;
      setGraphData(g);
      const delta = newCount - prevCount;
      showToast(`Graph updated${delta > 0 ? ` — ${delta} new node${delta !== 1 ? "s" : ""} ingested` : " — graph refreshed"}`);
    }).catch(() => {
      showToast("Graph refreshed after ingest");
    });
  }

  function handleProceedToWorkspace() {
    setWorkspaceOpen(true);
    setTab("graph");
  }

  function copyReportAsMarkdown() {
    if (!report) return;
    const lines = [`# ${report.title}`, ""];
    for (const s of report.sections || []) {
      lines.push(`## ${s.heading}`);
      lines.push(s.content);
      lines.push("");
    }
    navigator.clipboard.writeText(lines.join("\n")).catch(() => {});
  }

  if (!activeCase) {
    return <CaseHome onOpen={(caseRecord) => { setActiveCase(caseRecord); setWorkspaceOpen(false); setTab("upload"); }} />;
  }

  return (
    <div className="app">
      {toast && (
        <div className="toast">{toast}</div>
      )}

      <header>
        <div className="header-left">
          <div className="header-logo">🔍</div>
          <div className="header-title-group">
            <h1>ColdCache</h1>
            <span className="header-case-label">{activeCase.title}{activeCase.reference_number ? ` · ${activeCase.reference_number}` : ""}</span>
          </div>

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
          
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <button className="btn-improve" onClick={() => { setActiveCase(null); setWorkspaceOpen(false); }} title="Return to case list">All Cases</button>
            <button
              className="btn-improve"
              onClick={() => setShowGuide(true)}
              style={{ background: "linear-gradient(135deg,#1a1f2a 0%,#0d1220 100%)", borderColor: "var(--accent)", color: "var(--accent)" }}
              title="What does each tab do?"
            >
              User Manual
            </button>
            
            
          </div>
        </div>
      </header>

      {workspaceOpen && (
        <div className="stats-ribbon">
         <span className="stat-item">
          <span className="stat-key" style={{color:"var(--muted)"}}>ACTIVE CASE:</span>
          <span className="stat-val" style={{color:"var(--text)"}}>Daniel Marsh · Millbrook / Riverside</span>
        </span>
        <span className="stat-item">
          <span className="stat-dot" style={{background:"var(--accent)"}}/>
          <span className="stat-val">{stats.nodes}</span>
          <span className="stat-key">graph nodes</span>
        </span>
        <span className="stat-sep">·</span>
        <span className="stat-item">
          <span className="stat-dot" style={{background:"var(--win)"}}/>
          <span className="stat-val">{stats.docs}</span>
          <span className="stat-key">docs ingested</span>
        </span>
        <span className="stat-sep">·</span>
        <span className="stat-sep">·</span>
        
        <span className="stat-item alibi-break">
          <span className="stat-key" style={{color:"var(--muted)"}}> STATUS:</span>
          <span style={{color:"var(--danger)"}}>⚠</span>
          <span className="stat-key" style={{color:"var(--danger)"}}>alibi break detected</span>
        </span>
        <span className="stat-sep stat-sep-right">·</span>
       
      </div>
      )}

      {!workspaceOpen ? (
        <div className="single-view" style={{ marginTop: 16 }}>
          <div className="tab-window">
            <div className="workspace-window-header">
              <button className="back-to-desk" style={{ cursor: "default", opacity: 0.85 }}>
                Import Case Files and Data
              </button>
            </div>

            <main>
              <div className="tab-panel-fade">
                <CaseImportPanel caseId={activeCase.id} onGraphUpdated={handleGraphUpdated} onNext={handleProceedToWorkspace} />
              </div>
            </main>
          </div>
        </div>
      ) : (
        <div className="workspace-split" style={{ display: "grid", gridTemplateColumns: "minmax(320px, 1.2fr) minmax(360px, 420px)", gap: 16, marginTop: 16 }}>
          <div>
            <div className="tab-window">
              <div className="workspace-window-header">
                <button className="back-to-desk" onClick={() => { setWorkspaceOpen(false); setTab("upload"); }}>
                  ← Import Case Files and Data
                </button>
              </div>

              <nav className="sub-nav">
                {NAV_TABS.map((t) => (
                  <button
                    key={t.id}
                    className={tab === t.id ? "active" : ""}
                    onClick={() => setTab(t.id)}
                    title={t.blurb}
                  >
                    <span className="tab-icon">{t.icon}</span>
                    <span className="tab-label">{t.label}</span>
                  </button>
                ))}
              </nav>

              <main>
                <div key={tab} className="tab-panel-fade">
                  {tab === "graph" && (
                    <GraphPanel
                      justImproved={justImproved}
                      graphData={graphData}
                      onGraphLoaded={setGraphData}
                      caseId={activeCase.id}
                    />
                  )}
                  {tab === "timeline" && <TimelinePanel />}
                  {tab === "interrogation" && <InterrogationPanel />}
                  {tab === "whatif" && <WhatIfPanel />}
                </div>
              </main>
            </div>
          </div>

          <aside className="chat-aside" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <ChatPanel caseId={activeCase.id} />
          </aside>
        </div>
      )}

      {showGuide && (
        <div className="report-modal-overlay" onClick={closeGuide}>
          <div className="report-modal guide-modal" onClick={(e) => e.stopPropagation()}>
            <button className="report-close" onClick={closeGuide}>×</button>
            <h2 className="report-title">🔍 How ColdCache works</h2>
            <p style={{ color: "var(--muted)", fontSize: 14, marginTop: -8, marginBottom: 20 }}>
              This is a graph-vector investigative co-pilot for cold cases. Every tab below is a
              different lens on the same underlying case graph. Click any row to jump straight there.
            </p>
            <div className="guide-list">
              {GUIDE_TABS.map((t) => (
                <button
                  key={t.id}
                  className="guide-row"
                  onClick={() => { setTab(t.id); closeGuide(); }}
                >
                  <span className="guide-row-icon">{t.icon}</span>
                  <span className="guide-row-body">
                    <span className="guide-row-title">{t.label}</span>
                    <span className="guide-row-blurb">{t.blurb}</span>
                    <span className="guide-row-try">{t.tryText}</span>
                  </span>
                </button>
              ))}
            </div>
            <button className="report-copy-btn" onClick={closeGuide} style={{ marginTop: 16 }}>
              Got it, let's go
            </button>
          </div>
        </div>
      )}

      {showReport && (
        <div className="report-modal-overlay" onClick={() => setShowReport(false)}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()}>
            <button className="report-close" onClick={() => setShowReport(false)}>×</button>
            {reportLoading ? (
              <p style={{ color: "var(--muted)", textAlign: "center", padding: "32px 0" }}>Generating report…</p>
            ) : !report ? (
              <p style={{ color: "var(--danger)", textAlign: "center", padding: "32px 0" }}>Failed to load report.</p>
            ) : (
              <>
                <h2 className="report-title">{report.title}</h2>
                {(report.sections || []).map((s, i) => (
                  <div key={i} className="report-section">
                    <div className="report-section-heading">{s.heading}</div>
                    <div className="report-section-content">{s.content}</div>
                  </div>
                ))}
                <button className="report-copy-btn" onClick={copyReportAsMarkdown}>
                  Copy as Markdown
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
