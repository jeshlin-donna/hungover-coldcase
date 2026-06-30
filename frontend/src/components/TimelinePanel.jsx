import { useEffect, useState } from "react";
import { api } from "../api.js";

// Static enriched incident data aligned with mock/timeline.json
const INCIDENTS = [
  {
    date: "2023-03-03",
    case: "MH-2023-0312",
    jurisdiction: "Maple Heights",
    jurKey: "clearwater",
    title: "Burglary — 14 Maple Heights Dr",
    summary:
      "Rear slider pried, doorbell cam obscured, electronics + small safe taken. Witness: dark blue sedan, partial plate 8K.",
    tool: "Pry bar · 8mm · left-edge nick",
    taken: "Electronics, small safe",
    dotClass: "clearwater",
  },
  {
    date: "2023-11-19",
    case: "RV-2023-0788",
    jurisdiction: "Riverside",
    jurKey: "hale",
    title: "Burglary — 902 Riverside Lane",
    summary:
      "Same MO in a different county. 8mm left-nick tool signature. Witness: dark blue sedan. No shared records system with Maple Heights.",
    tool: "Pry bar · 8mm · left-edge nick",
    taken: "Jewelry, electronics",
    dotClass: "hale",
  },
  {
    date: "2025-02-04",
    case: "MH-2025-0102",
    jurisdiction: "Maple Heights",
    jurKey: "clearwater",
    title: "Burglary — 31 Maple Heights Ct",
    summary:
      "Third job, same signature. Cam spray missed the lens edge → 4-sec clip caught the plate.",
    tool: "Pry bar · 8mm · left-edge nick",
    taken: "Electronics, power tools",
    dotClass: "clearwater",
  },
  {
    date: "2025-02-10",
    case: "MH-2025-0102",
    jurisdiction: "Maple Heights",
    jurKey: "arrest",
    title: "Arrest — Daniel R. Marsh",
    summary:
      "Plate → owner. Pry bar recovered matches 8mm + left nick across all three cases. Confession.",
    tool: "Pry bar (recovered, match confirmed)",
    taken: null,
    dotClass: "arrest",
    isArrest: true,
  },
];

function jurBadgeClass(jurKey) {
  if (jurKey === "clearwater") return "jur-badge jur-clearwater";
  if (jurKey === "hale") return "jur-badge jur-hale";
  return "jur-badge jur-arrest";
}

function jurLabel(jurKey) {
  if (jurKey === "clearwater") return "Clearwater County";
  if (jurKey === "hale") return "Hale County";
  return "Maple Heights PD";
}

export default function TimelinePanel() {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    api.timeline()
      .then((d) => setEvents(d.events))
      .catch(() => setEvents(INCIDENTS));
  }, []);

  // Use our enriched static data for display — events from the API confirm
  // the data is present, but INCIDENTS has the richer fields.
  const incidents = INCIDENTS;

  return (
    <div className="panel timeline-panel">
      <div className="timeline-header">
        <div>
          <h2>Case Timeline</h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Three incidents across two jurisdictions that shared no records system.
          </p>
        </div>
        <div style={{ fontSize: 12, color: "var(--muted)", textAlign: "right" }}>
          <div>Mar 2023 → Feb 2025 · 23 months</div>
        </div>
      </div>

      <div className="timeline-track">
        <div className="timeline-line" />
        <div className="timeline-incidents">
          {incidents.map((inc, i) => (
            <div key={i} className="incident">
              <div className="incident-dot-wrap">
                <div className={`incident-dot ${inc.dotClass}`} />
                <div className="incident-stem" />
              </div>

              <div className={`incident-card${inc.isArrest ? " arrest" : ""}`}>
                <div className="incident-date">{inc.date}</div>
                <div className="incident-case">{inc.case}</div>
                <span className={jurBadgeClass(inc.jurKey)}>{jurLabel(inc.jurKey)}</span>
                <div className="incident-title">{inc.title}</div>
                <div className="incident-summary">{inc.summary}</div>

                {inc.tool && (
                  <div className="incident-tool">
                    <span style={{ color: "var(--gold)" }}>⚒</span>
                    <span>{inc.tool}</span>
                  </div>
                )}

                {inc.taken && (
                  <div className="incident-tool">
                    <span style={{ color: "var(--muted)" }}>↗</span>
                    <span>Taken: <span>{inc.taken}</span></span>
                  </div>
                )}

                {inc.isArrest && (
                  <div className="cross-ref">
                    <strong>Cross-reference detected</strong> — 23 months after the first
                    incident. Cognee would have connected the tool signature across
                    jurisdictions on day 1.
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="tl-legend">
        <div className="tl-legend-item">
          <div className="tl-dot" style={{ background: "var(--accent)" }} />
          Clearwater County (Maple Heights PD)
        </div>
        <div className="tl-legend-item">
          <div className="tl-dot" style={{ background: "var(--warning)" }} />
          Hale County (Riverside PD)
        </div>
        <div className="tl-legend-item">
          <div className="tl-dot" style={{ background: "var(--win)" }} />
          Arrest
        </div>
        <div
          className="tl-legend-item"
          style={{
            marginLeft: "auto",
            fontStyle: "italic",
            color: "var(--muted)",
          }}
        >
          No shared records system existed between Clearwater and Hale Counties.
        </div>
      </div>
    </div>
  );
}
