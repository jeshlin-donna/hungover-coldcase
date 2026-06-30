import { useEffect, useState } from "react";
import { api } from "../api.js";

const MOCK_GAPS = {
  suspect: "Daniel R. Marsh",
  case_focus: "RV-2023-0788",
  cognee_insight:
    "Graph traversal identified 3 temporal voids in the known node timeline. The Nov 18–19 gap falls precisely on the RV-0788 window. No alibi node exists with verified edges for that period — the alibi:marsh-nov19 node's only corroboration is self-reported.",
  gaps: [
    {
      id: "gap-1",
      urgency: "CRITICAL",
      start: "2023-11-18T22:00:00",
      end: "2023-11-19T06:00:00",
      duration_hrs: 8,
      label: "Night of RV-2023-0788 — alibi contradicted",
      nearby_events: [
        "Card record: motel check-in at 00:48 (4.2 mi from scene)",
        "Alibi claim: '300 miles out of state' — no corroborating node",
        "RV-0788 incident window: 02:00–04:00",
      ],
      recommendation:
        "Pull cell tower ping data for Marsh's registered number for Nov 18 10 PM – Nov 19 6 AM. Cross-reference motel check-in with surveillance footage. Cell provider subpoena will confirm presence within 4 miles of the Riverside scene.",
    },
    {
      id: "gap-2",
      urgency: "HIGH",
      start: "2023-03-03T01:30:00",
      end: "2023-03-03T05:00:00",
      duration_hrs: 3.5,
      label: "MH-2023-0312 incident window — no alibi filed",
      nearby_events: [
        "MH-0312 window: 02:00–04:00 (within gap)",
        "No alibi statement exists for this night",
        "Marsh's vehicle (plate 8K·) seen at scene per witness",
      ],
      recommendation:
        "Canvas Marsh's known associates for Mar 3 2023. Pull gas station receipts along the Maple Heights corridor for that night. The plate witness can be re-interviewed for positive ID.",
    },
    {
      id: "gap-3",
      urgency: "HIGH",
      start: "2025-02-03T23:00:00",
      end: "2025-02-04T04:00:00",
      duration_hrs: 5,
      label: "MH-2025-0102 — tool recovery window",
      nearby_events: [
        "MH-0102 occurred Feb 4 between midnight and 3 AM",
        "Pry bar recovered from Marsh's vehicle Feb 10",
        "6-day gap between incident and tool recovery — storage location unknown",
      ],
      recommendation:
        "Obtain warrant for any storage unit or secondary property linked to Marsh. The 6-day gap suggests the tool was stored at a non-residential location. Check self-storage facilities within 10 miles of both jurisdictions.",
    },
  ],
};

function formatDateRange(start, end, hrs) {
  const s = new Date(start);
  const e = new Date(end);
  const opts = { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" };
  const sf = s.toLocaleString("en-US", opts);
  const ef = e.toLocaleString("en-US", { hour: "numeric", minute: "2-digit" });
  const hrsLabel = hrs % 1 === 0 ? `${hrs}hrs` : `${hrs}hrs`;
  return `${sf} – ${ef} · ${hrsLabel}`;
}

export default function MissingHoursPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .missingHours()
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => { setData(MOCK_GAPS); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <div className="panel missing-hours-panel">
        <div className="skeleton">
          <div className="skel-line" style={{ height: 18, width: "40%" }} />
          <div className="skel-line" style={{ height: 12, width: "60%", marginTop: 8 }} />
          <div className="skel-line" style={{ height: 120, width: "100%", marginTop: 16 }} />
        </div>
      </div>
    );
  }

  const d = data || MOCK_GAPS;

  return (
    <div className="panel missing-hours-panel">
      <div className="mh-header">
        <div>
          <h2 className="mh-title">Missing Hours — Information Bounty</h2>
          <p className="mh-subtitle">
            Gaps the detective needs to fill to close the case ·{" "}
            <span style={{ color: "var(--accent)" }}>{d.suspect}</span> ·{" "}
            <span style={{ fontFamily: "ui-monospace,monospace", fontSize: 12 }}>
              {d.case_focus}
            </span>
          </p>
        </div>
        <div className="mh-count-badge">{d.gaps.length} unaccounted gaps</div>
      </div>

      <div className="gap-list">
        {d.gaps.map((gap) => (
          <div key={gap.id} className="gap-card">
            <div className="gap-card-top">
              <span className={`urgency-badge ${gap.urgency.toLowerCase()}`}>
                {gap.urgency}
              </span>
              <span className="gap-time-range">
                {formatDateRange(gap.start, gap.end, gap.duration_hrs)}
              </span>
            </div>

            <div className="gap-label">{gap.label}</div>

            <ul className="gap-events">
              {gap.nearby_events.map((ev, i) => (
                <li key={i}>{ev}</li>
              ))}
            </ul>

            <div className="gap-recommendation">
              <span className="rec-prefix">Recommended action</span>
              {gap.recommendation}
            </div>
          </div>
        ))}
      </div>

      {d.cognee_insight && (
        <div className="cognee-insight-box">
          <span className="cognee-insight-label">Cognee graph insight</span>
          <p className="cognee-insight-text">{d.cognee_insight}</p>
        </div>
      )}
    </div>
  );
}
