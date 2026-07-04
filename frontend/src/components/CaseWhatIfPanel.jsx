import { useState } from "react";
import { api } from "../api.js";

export default function CaseWhatIfPanel({ caseId }) {
  const [hypothesis,setHypothesis]=useState(""); const [result,setResult]=useState(null); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function run(){if(!hypothesis.trim())return;setLoading(true);setError("");try{setResult(await api.caseWhatIf(caseId,hypothesis.trim()));}catch(e){setError(e.message);}finally{setLoading(false);}}
  return <div className="panel whatif-panel"><h2 className="whatif-title">What-If — Hypothesis Sandbox</h2><p className="muted-copy">Evaluate a hypothesis against this case without changing verified evidence or its graph.</p><textarea className="hypothesis-textarea" rows={4} value={hypothesis} onChange={(e)=>setHypothesis(e.target.value)} placeholder="What if this timestamp is incorrect?"/><button className="whatif-run-btn" onClick={run} disabled={loading||!hypothesis.trim()}>{loading?"Evaluating…":"Run case-scoped analysis"}</button>{error&&<div className="upload-error">{error}</div>}{result&&<div className="whatif-result"><div className="narrative-box"><p>{result.narrative}</p></div><span className={`ingested-mode-badge ${result.mode}`}>{result.mode} mode</span></div>}</div>;
}
