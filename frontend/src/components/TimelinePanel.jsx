import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function TimelinePanel() {
  const [events, setEvents] = useState([]);
  useEffect(() => { api.timeline().then((d) => setEvents(d.events)); }, []);

  return (
    <div className="panel timeline">
      {events.map((e, i) => (
        <div key={i} className="event">
          <div className="dot" />
          <div className="event-body">
            <div className="event-head">
              <span className="date">{e.date}</span>
              <span className={`jur ${e.jurisdiction.replace(/\s/g, "")}`}>{e.jurisdiction}</span>
              <span className="case">{e.case}</span>
            </div>
            <h4>{e.title}</h4>
            <p>{e.summary}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
