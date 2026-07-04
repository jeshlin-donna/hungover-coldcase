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

// Date range for the slider: 2023-01-01 to 2025-12-31 by month
const SLIDER_MIN_YEAR = 2023;
const SLIDER_MIN_MONTH = 0; // January = 0
const SLIDER_MAX_YEAR = 2025;
const SLIDER_MAX_MONTH = 11; // December = 11

function monthIndexToDate(idx) {
  // idx 0 = Jan 2023, idx 35 = Dec 2025
  const year = SLIDER_MIN_YEAR + Math.floor(idx / 12);
  const month = idx % 12;
  return new Date(year, month, 1);
}

function totalMonths() {
  const minIdx = SLIDER_MIN_YEAR * 12 + SLIDER_MIN_MONTH;
  const maxIdx = SLIDER_MAX_YEAR * 12 + SLIDER_MAX_MONTH;
  return maxIdx - minIdx;
}

function formatSliderDate(d) {
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function incidentDate(inc) {
  return new Date(inc.date);
}

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

// timeFilter: a Date object — show incidents at or before this date
export default function TimelinePanel({ timeFilter }) {
  const [events, setEvents] = useState(null);
  const [sliderIdx, setSliderIdx] = useState(totalMonths()); // start at max

  useEffect(() => {
    api
      .timeline()
      .then((d) => setEvents(d.events))
      .catch(() => setEvents(INCIDENTS));
  }, []);

  const maxIdx = totalMonths();
  const sliderDate = monthIndexToDate(sliderIdx);

  // If a timeFilter prop is passed use it, otherwise use internal slider
  const cutoffDate = timeFilter || sliderDate;

  // Filter incidents: show only those at or before cutoff
  const visibleIncidents = INCIDENTS.filter(
    (inc) => incidentDate(inc) <= cutoffDate
  );

  const isFiltered = sliderIdx < maxIdx || timeFilter;

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

      {/* Temporal slider */}
      <div className="temporal-slider-wrap">
        <div className="temporal-slider-label-row">
          <span className="temporal-slider-label">Temporal filter</span>
          <span className="temporal-slider-date">
            {isFiltered && sliderIdx < maxIdx
              ? `Showing events up to ${formatSliderDate(sliderDate)}`
              : "All events shown"}
          </span>
          {sliderIdx < maxIdx && (
            <button
              className="temporal-reset-btn"
              onClick={() => setSliderIdx(maxIdx)}
            >
              Reset
            </button>
          )}
        </div>
        <input
          type="range"
          className="temporal-slider"
          min={0}
          max={maxIdx}
          step={1}
          value={sliderIdx}
          onChange={(e) => setSliderIdx(Number(e.target.value))}
        />
        <div className="temporal-slider-ends">
          <span>Jan 2023</span>
          <span>Dec 2025</span>
        </div>
      </div>

      {visibleIncidents.length === 0 ? (
        <div className="temporal-empty">
          <p>No incidents before {formatSliderDate(sliderDate)}. Drag the slider forward.</p>
        </div>
      ) : (
        <div className="timeline-track">
          <div className="timeline-line" />
          <div
            className="timeline-incidents"
            style={{
              gridTemplateColumns: `repeat(${Math.min(visibleIncidents.length, 4)}, 1fr)`,
            }}
          >
            {visibleIncidents.map((inc, i) => (
              <div key={i} className={`incident${isFiltered ? " incident-fade-in" : ""}`}>
                <div className="incident-dot-wrap">
                  <div className={`incident-dot ${inc.dotClass}`} />
                  <div className="incident-stem" />
                </div>

                <div className={`incident-card jur-accent-${inc.jurKey}${inc.isArrest ? " arrest" : ""}`}>
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
                      <span>
                        Taken: <span>{inc.taken}</span>
                      </span>
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
      )}

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
