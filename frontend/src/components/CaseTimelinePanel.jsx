import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function CaseTimelinePanel({ caseId }) {
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.caseTimeline(caseId).then((data) => setEvents(data.events || [])).catch((e) => setError(e.message)); }, [caseId]);
  return <div className="panel timeline-panel"><div className="timeline-header"><div><h2>Case Timeline</h2><p style={{color:"var(--muted)"}}>Durable evidence activity for this case.</p></div></div>
    {error && <div className="upload-error">{error}</div>}
    {events === null ? <div className="skeleton"><div className="skel-line" /></div> : events.length === 0 ? <div className="temporal-empty"><p>No evidence events yet. Import files to begin this timeline.</p></div> :
      <div className="case-event-list">{events.map((event) => <div className="incident-card" key={event.evidence_id}><div className="incident-date">{new Date(event.date).toLocaleString()}</div><div className="incident-title">{event.title}</div><div className="incident-summary">Status: {event.summary.replaceAll("_", " ")}</div></div>)}</div>}
  </div>;
}
