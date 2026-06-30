import { useEffect, useState } from "react";
import { api } from "../api.js";

const MOCK_INTERROGATION = {
  suspect: "Daniel R. Marsh",
  case: "RV-2023-0788",
  strategy:
    "Lead with the card records. He doesn't know we have the motel receipt tied to the timestamp. Let him commit to the '300 miles out of state' alibi fully before you surface it. The contradiction is airtight — use it as the pivot.",
  questions: [
    {
      number: 1,
      type: "OPEN",
      text: "Walk me through where you were on the evening of November 18th, 2023 and into the morning of the 19th. Take your time.",
      expected_response:
        "Expects the alibi claim to be re-stated: '300 miles away, out of state.' Marsh will likely volunteer specifics to seem cooperative.",
      trap: null,
      evidence_held_back: null,
    },
    {
      number: 2,
      type: "OPEN",
      text: "You mentioned being out of state. Can you tell me the name of where you stayed that night?",
      expected_response:
        "Marsh may hesitate here. If he names a hotel, note it — there will be no record. If he says he drove through, probe for fuel receipts.",
      trap: "If he names a location, that location will be verifiably false given the card record.",
      evidence_held_back: "Card record placing him 4.2 miles from the scene at 00:48.",
    },
    {
      number: 3,
      type: "CONFRONTATION",
      text: "I'm going to show you something. This is a card transaction on your account — November 19th, 2023, 12:48 AM, at the Riverside Motor Inn, 902 Route 9. That's 4.2 miles from the Riverside Lane address. Can you explain this?",
      expected_response:
        "Expect denial or confusion. Marsh may claim the card was stolen or misused, or attempt to reframe the timeline.",
      trap: "The transaction is undeniable — his physical card was present. PIN entry confirmed at terminal.",
      evidence_held_back: "Cell tower data (if obtained) confirming device ping at same location.",
    },
    {
      number: 4,
      type: "FISHING",
      text: "You've worked with pry bars in your trade, right? What kind do you usually use for tight doorframe work?",
      expected_response:
        "Marsh may describe tools consistent with the 8mm signature without realizing the connection. Any mention of a flat blade with a nick is significant.",
      trap: null,
      evidence_held_back: "Forensic match of recovered pry bar to marks at all three scenes.",
    },
    {
      number: 5,
      type: "CONFRONTATION",
      text: "The pry bar we recovered from your vehicle — the forensic lab matched its 8mm profile and a distinctive left-edge nick to marks at all three scenes: Maple Heights 2023, Riverside 2023, and Maple Heights 2025. That's your tool at all three jobs. What do you want to tell me?",
      expected_response:
        "This is the closing confrontation. Marsh confessed when presented with this in the actual investigation. Expect either a full statement or a request for counsel.",
      trap: null,
      evidence_held_back: null,
    },
  ],
  weak_edges: [
    "No eyewitness directly places Marsh at the Riverside scene — vehicle witness only saw the sedan",
    "The alibi:marsh-nov19 node has zero verified outbound edges — it is entirely self-reported",
    "Chain of custody for the pry bar has one gap: 6 days between incident and recovery",
  ],
  cognee_insight:
    "Graph traversal identified that the alibi node has no corroborating edges — it is a terminal node with no witness, no digital, and no physical corroboration. The card record node, by contrast, has three cross-referencing edges: the motel, Marsh's account, and the timestamp coinciding with the RV-0788 window.",
};

const TYPE_COLORS = {
  OPEN: { bg: "rgba(88,166,255,0.12)", color: "#58a6ff", border: "rgba(88,166,255,0.3)" },
  CONFRONTATION: { bg: "rgba(248,81,73,0.12)", color: "#f85149", border: "rgba(248,81,73,0.3)" },
  FISHING: { bg: "rgba(227,179,65,0.12)", color: "#e3b341", border: "rgba(227,179,65,0.3)" },
};

export default function InterrogationPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedQ, setExpandedQ] = useState(null);

  useEffect(() => {
    api
      .interrogation("suspect:daniel-marsh", "RV-2023-0788")
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => { setData(MOCK_INTERROGATION); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <div className="panel interrogation-panel">
        <div className="skeleton">
          <div className="skel-line" style={{ height: 20, width: "55%" }} />
          <div className="skel-line" style={{ height: 60, width: "100%", marginTop: 12 }} />
          <div className="skel-line" style={{ height: 100, width: "100%", marginTop: 10 }} />
        </div>
      </div>
    );
  }

  const d = data || MOCK_INTERROGATION;

  return (
    <div className="panel interrogation-panel">
      <div className="int-header">
        <h2 className="int-title">Interrogation Co-Pilot</h2>
        <div className="int-meta">
          <span className="int-suspect">{d.suspect}</span>
          <span className="int-sep">·</span>
          <span style={{ fontFamily: "ui-monospace,monospace", fontSize: 12, color: "var(--muted)" }}>
            {d.case}
          </span>
        </div>
      </div>

      <div className="strategy-box">
        <span className="strategy-label">Strategy</span>
        <p className="strategy-text">{d.strategy}</p>
      </div>

      <div className="question-list">
        {d.questions.map((q) => {
          const typeStyle = TYPE_COLORS[q.type] || TYPE_COLORS.OPEN;
          const isExpanded = expandedQ === q.number;
          return (
            <div
              key={q.number}
              className="question-card"
              onClick={() => setExpandedQ(isExpanded ? null : q.number)}
            >
              <div className="q-card-top">
                <div className="q-num-type">
                  <span className="q-num">Q{q.number}</span>
                  <span
                    className="q-type-badge"
                    style={{
                      background: typeStyle.bg,
                      color: typeStyle.color,
                      borderColor: typeStyle.border,
                    }}
                  >
                    {q.type}
                  </span>
                  {q.evidence_held_back && (
                    <span className="evidence-held-chip">EVIDENCE HELD BACK</span>
                  )}
                </div>
                <span className="q-expand-icon">{isExpanded ? "▲" : "▼"}</span>
              </div>

              <p className="q-text">{q.text}</p>

              {isExpanded && (
                <div className="q-detail">
                  <div className="q-expected">
                    <span className="q-detail-label">Expected response</span>
                    <p>{q.expected_response}</p>
                  </div>

                  {q.trap && (
                    <div className="trap-row">
                      <span className="trap-icon">⚠</span>
                      <div>
                        <span className="trap-label">Trap</span>
                        <p className="trap-text">{q.trap}</p>
                      </div>
                    </div>
                  )}

                  {q.evidence_held_back && (
                    <div className="evidence-held-row">
                      <span className="trap-label" style={{ color: "var(--warning)" }}>
                        Evidence held back
                      </span>
                      <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--muted)" }}>
                        {q.evidence_held_back}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {d.weak_edges && d.weak_edges.length > 0 && (
        <div className="weak-edges-section">
          <h4 className="we-title">Weak edges to be aware of</h4>
          <ul className="we-list">
            {d.weak_edges.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {d.cognee_insight && (
        <div className="cognee-insight-box">
          <span className="cognee-insight-label">Cognee graph insight</span>
          <p className="cognee-insight-text">{d.cognee_insight}</p>
        </div>
      )}
    </div>
  );
}
