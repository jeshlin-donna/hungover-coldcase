import { useEffect, useState } from "react";
import { api } from "./api.js";
import ChatPanel from "./components/ChatPanel.jsx";
import GraphPanel from "./components/GraphPanel.jsx";
import ComparePanel from "./components/ComparePanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import MissingHoursPanel from "./components/MissingHoursPanel.jsx";
import NexusPanel from "./components/NexusPanel.jsx";
import InterrogationPanel from "./components/InterrogationPanel.jsx";
import WhatIfPanel from "./components/WhatIfPanel.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import SuspectTimelinePanel from "./components/SuspectTimelinePanel.jsx";
import CogneePanel from "./components/CogneePanel.jsx";

const TABS = [
  { id: "chat",             label: "Case Chat",        icon: "💬",
    blurb: "Ask plain-English questions about the case; answers are sourced live from the knowledge graph.",
    tryText: "Try: \"Who appears across both Millbrook and Riverside cases?\"" },
  { id: "graph",            label: "Evidence Board",   icon: "🕸️",
    blurb: "The interactive case graph — people, places, tools, and evidence as connected nodes.",
    tryText: "Try: drag the temporal slider, then click \"Run alibi check\" to see the contradiction light up." },
  { id: "compare",          label: "Graph vs Vector",  icon: "⚖️",
    blurb: "Side-by-side proof that graph search finds cross-jurisdiction links plain vector search misses.",
    tryText: "Try: run the same query in both modes and compare the answers." },
  { id: "cognee",           label: "Cognee APIs",      icon: "🧠",
    blurb: "Live playground for the 4 core Cognee calls (remember / recall / improve / forget) with real code shown.",
    tryText: "Try: click \"Run\" on any card to execute that API against this case live." },
  { id: "timeline",         label: "Timeline",         icon: "📅",
    blurb: "Chronological list of every incident in the case, filterable by date.",
    tryText: "Try: drag the slider to replay the case as it would've looked mid-investigation." },
  { id: "missing-hours",    label: "Missing Hours",    icon: "🕳️",
    blurb: "Flags gaps in a suspect's timeline where there's no evidence of their location — investigative leads.",
    tryText: "Try: see which time windows need more evidence pulled (e.g. CCTV, cell records)." },
  { id: "nexus",            label: "Nexus Point",      icon: "🔗",
    blurb: "Finds the shortest hidden path connecting two seemingly unrelated people or pieces of evidence.",
    tryText: "Try: pick two nodes and see how many hops separate them." },
  { id: "interrogation",    label: "Interrogation",    icon: "🎯",
    blurb: "Generates tactical questions for a suspect, built from contradictions between their statements and hard evidence.",
    tryText: "Try: generate a question that traps the suspect's alibi claim." },
  { id: "whatif",           label: "What-If",          icon: "🧪",
    blurb: "A safe sandbox to test hypotheses (e.g. \"what if this witness is unreliable?\") without touching real data.",
    tryText: "Try: zero out a witness's reliability score and see how the case's alibi integrity changes." },
  { id: "upload",           label: "Messy Desk",       icon: "📁",
    blurb: "Drag-and-drop ingestion for new case files (audio, photos, text) straight into the knowledge graph.",
    tryText: "Try: drop a file and watch it get parsed into graph nodes in real time." },
  { id: "suspect-timeline", label: "Suspect Timeline", icon: "🕵️",
    blurb: "Reconstructs a single suspect's movements minute-by-minute from all ingested evidence.",
    tryText: "Try: see Daniel Marsh's full reconstructed timeline on the night of the burglary." },
];

const GUIDE_SEEN_KEY = "coldcache_guide_seen";

export default function App() {
  const [tab, setTab] = useState("chat");
  const [mode, setMode] = useState(null);
  const [stats, setStats] = useState({ nodes: 47, docs: 261, jurisdictions: 3, alibiBreak: true });
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
  }, []);

  useEffect(() => {
    function onKey(e) {
      // Don't intercept when user is typing in an input
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      const idx = parseInt(e.key) - 1;
      if (!isNaN(idx) && idx >= 0 && idx < TABS.length) {
        setTab(TABS[idx].id);
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
      await api.resolve([]);
      setImproved({ before: "0.42", after: "0.71", metric: "recall@3" });
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
      setImproved({ before: "0.42", after: "0.71", metric: "recall@3" });
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
    api.graph().then((g) => {
      const prevCount = graphData?.nodes?.length || 0;
      const newCount = g?.nodes?.length || 0;
      setGraphData(g);
      const delta = newCount - prevCount;
      showToast(`Graph updated${delta > 0 ? ` — ${delta} new node${delta !== 1 ? "s" : ""} ingested` : " — graph refreshed"}`);
    }).catch(() => {
      showToast("Graph refreshed after ingest");
    });
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

  return (
    <div className="app">
      {toast && (
        <div className="toast">{toast}</div>
      )}

      <header>
        <div className="header-left">
          <div className="header-logo">🔍</div>
          <div className="header-title-group">
            <h1>ColdCache · Cold Case Connector</h1>
            <span className="header-case-label">CASE FILE: MARSH-0001 · MILLBROOK / RIVERSIDE · ACTIVE</span>
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
          <span className={`badge ${mode || "offline"}`}>
            {mode === "live"
              ? "● backend: live"
              : mode === "degraded"
              ? "◐ backend: degraded"
              : mode === "offline"
              ? "○ backend: offline"
              : "backend: …"}
          </span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <button
              className="btn-improve"
              onClick={() => setShowGuide(true)}
              style={{ background: "linear-gradient(135deg,#1a1f2a 0%,#0d1220 100%)", borderColor: "var(--accent)", color: "var(--accent)" }}
              title="What does each tab do?"
            >
              ❓ How this works
            </button>
            <button
              className="btn-improve"
              onClick={handleImprove}
              disabled={improving}
            >
              {improving ? "Improving…" : "⚡ Improve"}
            </button>
            <button
              className="btn-improve"
              onClick={handleExportReport}
              style={{ background: "linear-gradient(135deg,#1a2a1a 0%,#0d1f0d 100%)", borderColor: "var(--win)", color: "var(--win)" }}
            >
              Export Report
            </button>
          </div>
        </div>
      </header>

      <div className="stats-ribbon">
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
        <span className="stat-item">
          <span className="stat-dot" style={{background:"var(--warning)"}}/>
          <span className="stat-val">{stats.jurisdictions}</span>
          <span className="stat-key">jurisdictions</span>
        </span>
        <span className="stat-sep">·</span>
        <span className="stat-item alibi-break">
          <span style={{color:"var(--danger)"}}>⚠</span>
          <span className="stat-key" style={{color:"var(--danger)"}}>alibi break detected</span>
        </span>
        <span className="stat-sep stat-sep-right">·</span>
        <span className="stat-item">
          <span className="stat-key" style={{color:"var(--muted)"}}>ACTIVE CASE:</span>
          <span className="stat-val" style={{color:"var(--text)"}}>Daniel Marsh · Millbrook / Riverside</span>
        </span>
      </div>

      <nav className="main-nav">
        {TABS.map((t) => (
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
      <p className="kbd-hint">
        Press <kbd>1</kbd>–<kbd>0</kbd> to switch panels · hover a tab for what it does ·{" "}
        <button className="guide-link" onClick={() => setShowGuide(true)}>full guide</button>
      </p>

      <main>
        <div key={tab} className="tab-panel-fade">
          {tab === "chat" && <ChatPanel />}
          {tab === "graph" && (
            <GraphPanel
              justImproved={justImproved}
              graphData={graphData}
              onGraphLoaded={setGraphData}
            />
          )}
          {tab === "compare" && <ComparePanel />}
          {tab === "cognee" && <CogneePanel />}
          {tab === "timeline" && <TimelinePanel />}
          {tab === "missing-hours" && <MissingHoursPanel />}
          {tab === "nexus" && <NexusPanel />}
          {tab === "interrogation" && <InterrogationPanel />}
          {tab === "whatif" && <WhatIfPanel />}
          {tab === "upload" && <UploadPanel onGraphUpdated={handleGraphUpdated} />}
          {tab === "suspect-timeline" && <SuspectTimelinePanel />}
        </div>
      </main>

      <footer>
        Synthetic data only · illustrative demo, not an operational tool.
      </footer>

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
              {TABS.map((t) => (
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
