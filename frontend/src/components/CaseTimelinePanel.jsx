import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

// Rotating palette for jurisdictions beyond the two named CSS classes
// (jur-clearwater / jur-hale). Cycles so any number of departments still
// gets a distinct, glowing dot + badge color.
const PALETTE = [
  { dot: "clearwater" },
  { dot: "hale" },
];
const EXTRA_COLORS = ["#a371f7", "#f778ba", "#56d4dd", "#ff7b72"];

function paletteFor(index) {
  if (index < PALETTE.length) return PALETTE[index];
  const color = EXTRA_COLORS[(index - PALETTE.length) % EXTRA_COLORS.length];
  return { dot: null, color };
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  const d = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function CaseTimelinePanel({ caseId }) {
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  const [sliderIdx, setSliderIdx] = useState(null);

  useEffect(() => {
    setEvents(null);
    setError("");
    api.caseTimeline(caseId).then((data) => setEvents(data.events || [])).catch((e) => setError(e.message));
  }, [caseId]);

  const dated = useMemo(() => (events || []).filter((e) => e.date), [events]);
  const undated = useMemo(() => (events || []).filter((e) => !e.date), [events]);

  const jurisdictions = useMemo(() => {
    const seen = [];
    for (const e of dated) {
      const j = e.jurisdiction || "Unspecified jurisdiction";
      if (!seen.includes(j)) seen.push(j);
    }
    return seen;
  }, [dated]);

  const jurColor = useMemo(() => {
    const map = {};
    jurisdictions.forEach((j, i) => { map[j] = paletteFor(i); });
    return map;
  }, [jurisdictions]);

  const sortedDates = useMemo(() => dated.map((e) => e.date).sort(), [dated]);
  const minDate = sortedDates[0];
  const maxDate = sortedDates[sortedDates.length - 1];
  const span = minDate && maxDate ? Math.max(1, Math.round((new Date(maxDate) - new Date(minDate)) / 86400000)) : 0;

  const effectiveIdx = sliderIdx === null ? dated.length : sliderIdx;
  const visible = dated.slice(0, effectiveIdx);
  const isFiltered = effectiveIdx < dated.length;

  const cardClass = (event) => `incident-card${event.is_key_event ? " arrest" : ""}`;
  const dotClass = (event) => {
    if (event.is_key_event) return "incident-dot arrest";
    const jur = event.jurisdiction || "Unspecified jurisdiction";
    const pal = jurColor[jur] || {};
    return `incident-dot${pal.dot ? ` ${pal.dot}` : ""}`;
  };
  const dotStyle = (event) => {
    if (event.is_key_event) return undefined;
    const jur = event.jurisdiction || "Unspecified jurisdiction";
    const pal = jurColor[jur] || {};
    if (pal.color) return { background: pal.color, boxShadow: `0 0 8px ${pal.color}66` };
    return undefined;
  };
  const badgeClass = (event) => {
    const jur = event.jurisdiction || "Unspecified jurisdiction";
    const pal = jurColor[jur] || {};
    return `jur-badge${pal.dot ? ` jur-${pal.dot}` : ""}`;
  };
  const badgeStyle = (event) => {
    const jur = event.jurisdiction || "Unspecified jurisdiction";
    const pal = jurColor[jur] || {};
    if (pal.dot) return undefined; // uses jur-clearwater/jur-hale CSS classes instead
    const color = pal.color || "var(--muted)";
    return { background: `${color}22`, color, border: `1px solid ${color}55` };
  };

  const firstKeyEventIdx = visible.findIndex((e) => e.is_key_event);

  return (
    <div className="panel timeline-panel">
      <div className="timeline-header">
        <div>
          <h2>Case Timeline</h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Events extracted from verified evidence; missing dates remain explicitly unknown.
          </p>
        </div>
        {minDate && maxDate && (
          <div style={{ fontSize: 12, color: "var(--muted)", textAlign: "right" }}>
            <div>{formatDate(minDate)} → {formatDate(maxDate)}{span > 0 ? ` · ${span} day${span === 1 ? "" : "s"}` : ""}</div>
          </div>
        )}
      </div>

      {error && <div className="upload-error">{error}</div>}

      {events === null ? (
        <div className="skeleton"><div className="skel-line" /></div>
      ) : dated.length === 0 && undated.length === 0 ? (
        <div className="temporal-empty"><p>No evidence events yet. Import files to begin this timeline.</p></div>
      ) : (
        <>
          {dated.length > 1 && (
            <div className="temporal-slider-wrap">
              <div className="temporal-slider-label-row">
                <span className="temporal-slider-label">Temporal filter</span>
                <span className="temporal-slider-date">
                  {isFiltered ? `Showing events up to ${formatDate(visible[visible.length - 1]?.date)}` : "All events shown"}
                </span>
                {isFiltered && (
                  <button className="temporal-reset-btn" onClick={() => setSliderIdx(null)}>Reset</button>
                )}
              </div>
              <input
                type="range"
                className="temporal-slider"
                min={1}
                max={dated.length}
                step={1}
                value={effectiveIdx}
                onChange={(e) => setSliderIdx(Number(e.target.value))}
              />
              <div className="temporal-slider-ends">
                <span>{formatDate(minDate)}</span>
                <span>{formatDate(maxDate)}</span>
              </div>
            </div>
          )}

          {visible.length > 0 && (
            <div className="timeline-track">
              <div className="timeline-line" />
              <div className="timeline-incidents" style={{ gridTemplateColumns: `repeat(${Math.min(visible.length, 4)}, 1fr)` }}>
                {visible.map((event, i) => (
                  <div key={`${event.evidence_id}-${event.date}-${event.time || i}`} className={`incident${isFiltered ? " incident-fade-in" : ""}`}>
                    <div className="incident-dot-wrap">
                      <div className={dotClass(event)} style={dotStyle(event)} />
                      <div className="incident-stem" />
                    </div>
                    <div className={cardClass(event)}>
                      <div className="incident-date">{formatDate(event.date)}{event.time ? ` · ${event.time}` : ""}</div>
                      {event.case_ref && <div className="incident-case">{event.case_ref}</div>}
                      {event.jurisdiction && (
                        <span className={badgeClass(event)} style={badgeStyle(event)}>{event.jurisdiction}</span>
                      )}
                      <div className="incident-title">{event.title}</div>
                      <div className="incident-summary">{(event.summary || "").replaceAll("_", " ")} · Source: {event.source}</div>
                      {event.is_key_event && i === firstKeyEventIdx && (
                        <div className="cross-ref">
                          <strong>Cross-reference detected</strong> — this event resolves the case, connecting evidence
                          gathered across {jurisdictions.length > 1 ? "multiple jurisdictions" : "this investigation"}.
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {undated.length > 0 && (
            <div className="case-event-list" style={{ marginTop: visible.length > 0 ? 24 : 0 }}>
              {undated.map((event, index) => (
                <div className="incident-card" key={`${event.evidence_id}-undated-${event.time || index}`}>
                  <div className="incident-date">Date not established{event.time ? ` · ${event.time}` : ""}</div>
                  <div className="incident-title">{event.title}</div>
                  <div className="incident-summary">{(event.summary || "").replaceAll("_", " ")} · Source: {event.source}</div>
                </div>
              ))}
            </div>
          )}

          {jurisdictions.length > 1 && (
            <div className="tl-legend">
              {jurisdictions.map((j) => {
                const pal = jurColor[j] || {};
                const color = pal.dot === "clearwater" ? "var(--accent)" : pal.dot === "hale" ? "var(--warning)" : pal.color || "var(--muted)";
                return (
                  <div className="tl-legend-item" key={j}>
                    <div className="tl-dot" style={{ background: color }} />
                    {j}
                  </div>
                );
              })}
              {dated.some((e) => e.is_key_event) && (
                <div className="tl-legend-item">
                  <div className="tl-dot" style={{ background: "var(--win)" }} />
                  Case-resolving event
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
