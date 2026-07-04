import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function CaseTimelinePanel({ caseId }) {
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.caseTimeline(caseId).then((data) => setEvents(data.events || [])).catch((e) => setError(e.message)); }, [caseId]);
  const eventWhen = (event) => {
    const date = event.date ? new Date(`${event.date}T00:00:00`).toLocaleDateString() : "Date not established";
    return event.time ? `${date} · ${event.time}` : date;
  };
  return <div className="panel timeline-panel"><div className="timeline-header"><div><h2>Case Timeline</h2><p style={{color:"var(--muted)"}}>Events extracted from verified evidence; missing dates remain explicitly unknown.</p></div></div>
    {error && <div className="upload-error">{error}</div>}
    {events === null ? <div className="skeleton"><div className="skel-line" /></div> : events.length === 0 ? <div className="temporal-empty"><p>No evidence events yet. Import files to begin this timeline.</p></div> :
      <div className="case-event-list">{events.map((event, index) => <div className="incident-card" key={`${event.evidence_id}-${event.date || "undated"}-${event.time || index}`}><div className="incident-date">{eventWhen(event)}</div><div className="incident-title">{event.title}</div><div className="incident-summary">{event.summary.replaceAll("_", " ")} · Source: {event.source}</div></div>)}</div>}
  </div>;
}
