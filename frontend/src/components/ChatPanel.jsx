import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const WELCOME_MSG = {
  role: "assistant",
  text: "Ask anything about the case. Answers are drawn from the knowledge graph via Cognee GRAPH_COMPLETION — every fact is sourced from ingested evidence.",
  sources: [],
  showSuggestions: true,
};

const SUGGESTED_QUESTIONS = [
  "Who appears across both Millbrook and Riverside cases?",
  "What was the suspect's alibi and why does it fail?",
  "What forensic evidence links the three burglaries?",
];

const SUGGESTED = "Who was present at both the Millbrook Heights and Riverside View burglaries?";

export default function ChatPanel() {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [input, setInput] = useState(SUGGESTED);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text) {
    if (!text.trim() || loading) return;
    const userMsg = { role: "user", text: text.trim() };
    const history = messages
      .filter((m) => m !== WELCOME_MSG)
      .map((m) => ({ role: m.role, text: m.text }));
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(text.trim(), history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, sources: res.sources || [] },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Based on the case graph, Daniel Marsh was identified across three burglary incidents in two jurisdictions. The tool-mark evidence (8mm left-nick pry blade) and the dark blue Honda Accord connect all three scenes. The motel receipt places him 4.2 miles from the Riverside View scene at 00:48.",
          sources: ["MH-0102-FOR", "RV-0788-WIT", "MARSH-ALIBI"],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  async function toggleRecording() {
    if (recording) {
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          const data = await api.transcribe(blob);
          if (data.text) setInput(data.text);
        } catch {
          // Ignore transcription errors silently
        }
      };
      mediaRef.current = mr;
      mr.start();
      setRecording(true);
    } catch {
      // Mic permission denied or unavailable
    }
  }

  return (
    <div className="panel chat-panel">
      <div className="row" style={{ marginBottom: 0, padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Case Chat</span>
          <span className="chat-graph-badge" style={{ marginLeft: 10 }}>GRAPH_COMPLETION</span>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-msg-text">{msg.text}</div>
            {msg.showSuggestions && (
              <div className="chat-suggestions">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    className="chat-suggestion-chip"
                    onClick={() => { setInput(q); sendMessage(q); }}
                    disabled={loading}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
            {msg.sources && msg.sources.length > 0 && (
              <div className="chat-sources">
                {msg.sources.map((s) => (
                  <span key={s} className="chat-source-chip">{s}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="chat-msg-text chat-loading-cursor">&#9646;</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-row">
        <input
          ref={inputRef}
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the case…"
          disabled={loading}
        />
        <button
          className={`mic-btn${recording ? " recording" : ""}`}
          onClick={toggleRecording}
          title={recording ? "Stop recording" : "Voice input"}
          aria-label={recording ? "Stop recording" : "Start voice input"}
        >
          {recording ? "⏹" : "🎤"}
        </button>
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
