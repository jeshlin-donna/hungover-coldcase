import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function SuspectTimelinePanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.suspectTimeline("daniel-marsh")
      .then(setData)
      .catch(() => setData(FALLBACK))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="panel" style={{ padding: 32, color: "var(--muted)", textAlign: "center" }}>
        Loading suspect timeline…
      </div>
    );
  }

  const events = data?.events || [];
  const narrative = data?.cognee_narrative;

  function isAlibiBreach(ev) {
    return ev.event && ev.event.toLowerCase().includes("motel");
  }

  return (
    <div className="panel stl-panel">
      <div style={{ marginBottom: 20 }}>
        <h2 className="stl-title">Suspect Movement Reconstruction</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: "4px 0 0" }}>
          Daniel R. Marsh — chronological event reconstruction across all cases
        </p>
      </div>

      {narrative && (
        <div className="cognee-insight-box" style={{ marginBottom: 24, marginTop: 0 }}>
          <span className="cognee-insight-label">Cognee Narrative</span>
          <p className="cognee-insight-text">{narrative}</p>
        </div>
      )}

      <div className="stl-events">
        {events.map((ev, i) => {
          const alibi = isAlibiBreach(ev);
          const highConf = ev.confidence > 0.9;
          return (
            <div key={i} className={`stl-event${alibi ? " stl-alibi" : ""}${highConf ? " stl-high-conf" : " stl-low-conf"}`}>
              <div className="stl-left">
                <div className="stl-date-badge">
                  <div className="stl-date">{ev.date}</div>
                  {ev.time && <div className="stl-time">{ev.time}</div>}
                </div>
                <div className="stl-line-seg" />
              </div>
              <div className="stl-card">
                {alibi && (
                  <div className="stl-alibi-flag">ALIBI CONTRADICTION</div>
                )}
                <div className="stl-location">{ev.location}</div>
                <div className="stl-event-text">{ev.event}</div>
                <div className="stl-conf-row">
                  <span className="stl-conf-label">Confidence</span>
                  <div className="stl-conf-track">
                    <div
                      className="stl-conf-bar"
                      style={{
                        width: `${Math.round(ev.confidence * 100)}%`,
                        background: ev.confidence > 0.9
                          ? "var(--win)"
                          : ev.confidence > 0.7
                          ? "var(--warning)"
                          : "var(--danger)",
                      }}
                    />
                  </div>
                  <span className="stl-conf-val">{Math.round(ev.confidence * 100)}%</span>
                </div>
                {ev.sources && ev.sources.length > 0 && (
                  <div className="stl-sources">
                    {ev.sources.map((s) => (
                      <span key={s} className="chip source">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const FALLBACK = {
  suspect: "daniel-marsh",
  events: [
    {
      date: "2023-03-03",
      time: "02:15",
      location: "Millbrook Heights",
      event: "Burglary at 412 Oakwood Drive — 8mm pry blade entry, electronics taken",
      confidence: 0.95,
      sources: ["MH-0102-NARR", "MH-0102-FOR"],
    },
    {
      date: "2023-03-03",
      time: "03:40",
      location: "I-94 corridor",
      event: "Dark blue Accord seen on traffic camera heading south",
      confidence: 0.72,
      sources: ["MH-0102-NARR"],
    },
    {
      date: "2023-11-19",
      time: "01:30",
      location: "Millbrook Heights",
      event: "Second burglary — same MO, same tool marks",
      confidence: 0.97,
      sources: ["MH-0312-FOR", "MH-0312-NARR"],
    },
    {
      date: "2025-02-04",
      time: "00:48",
      location: "Grand Stay Inn (4.2mi from scene)",
      event: "Motel check-in — contradicts alibi claim of being 300mi away",
      confidence: 0.99,
      sources: ["MARSH-RECEIPT", "MARSH-ALIBI"],
    },
    {
      date: "2025-02-04",
      time: "02:30",
      location: "Riverside View",
      event: "Burglary at 788 Riverside — third incident, arrested 6 days later",
      confidence: 0.99,
      sources: ["RV-0788-NARR", "RV-0788-FOR"],
    },
    {
      date: "2025-02-10",
      time: "14:00",
      location: "Riverside View PD",
      event: "Arrest — doorbell camera identified vehicle",
      confidence: 1.0,
      sources: ["MH-0102-ARR"],
    },
  ],
  mode: "degraded",
};
