# ColdCache — Progress Tracker

> **Last updated:** 2026-07-05 — deployment-readiness and production hardening pass.
> Primary architecture: durable multi-case workspace + legacy global demo compatibility.

Legend: ✅ done · 🔄 in progress · ⬜ todo

---

## ✅ Shipped in the merged codebase

### Case-scoped workspace
- ✅ Blank case home with create / archive / restore / delete
- ✅ Application-owned SQLite case store under configurable `COLDCACHE_DATA_DIR`
- ✅ Durable case file storage under the same persistent root
- ✅ Evidence analysis / ingestion / reindex jobs with recovery-friendly leases
- ✅ Replayable job events plus polling fallback
- ✅ One immutable Cognee dataset per case
- ✅ Case-scoped graph, chat, timeline, interrogation, what-if, report, hunch, and resolve routes
- ✅ Safe ingested-evidence deletion via dataset rebuild

### Reliability / fallback
- ✅ Groq rate-limit / degraded-reply fallback to local Ollama for Cognee recall
- ✅ Groq extraction fallback to local Ollama for cognify
- ✅ Groq vision fallback to local Ollama vision, then Claude last resort
- ✅ Groq transcription fallback to local Whisper
- ✅ `/health` exposes fallback activity
- ✅ Cognee retry-floor monkeypatch allows fallback to trigger quickly

### Current frontend
- ✅ Main shell uses `CaseHome`, `CaseImportPanel`, `GraphPanel`, `CaseTimelinePanel`, `CaseInterrogationPanel`, `CaseWhatIfPanel`, and `ChatPanel`
- ✅ Import queue rehydrates after reload
- ✅ Graph rebuild (`/cases/{id}/reindex`) is visible in the UI
- ✅ Header case label comes from the stored case title
- ✅ Model output renders as structured, contained text in Chat, Interrogation, and What-If
- ✅ Production CSP/security headers for Nginx, Cloudflare Pages, and Vercel

### Deployment readiness
- ✅ One-process production container for the embedded databases
- ✅ OCI-oriented Compose stack with persistent volume, HTTPS, and Basic Auth
- ✅ Exact CORS allowlist and optional trusted-host enforcement
- ✅ `/ready` checks writable persistent storage and SQLite
- ✅ Render blueprint corrected to a paid disk-capable plan (free Render is explicitly unsupported for persistence)
- ✅ Groq production template plus xAI Grok text configuration

### Legacy/global compatibility retained
- ✅ Benchmark / narrated demo / mock-compatible global routes still exist
- ✅ Global `/graph` stats now use real backend counts for `docs_ingested`
- ✅ Backend `/case-name` override + auto-label logic still works for the legacy global surface

---

## 🔄 In progress

- 🔄 Full 3-way benchmark run on the complete 261-document corpus
- 🔄 Content/docs cleanup so all developer-facing docs describe the post-merge architecture accurately
- 🔄 Decide whether to remove or fully re-integrate leftover legacy frontend components that are no longer mounted by `App.jsx`

---

## ⬜ Remaining follow-up work

- ⬜ Regenerate full benchmark numbers and update README/blog copy with final Cognee vector/graph metrics
- ⬜ Decide whether the current frontend should expose case-scoped report and suspect-timeline UI again
- ⬜ Decide whether `/case-name` should be removed, hidden, or re-wired in a multi-case-safe way
- ⬜ Add per-user identity, audit logging, and application-level rate limits before handling sensitive real-world evidence (the private deployment stack currently uses edge Basic Auth)

---

## Practical repo split to remember

| Area | Status | Notes |
|---|---|---|
| Current app UI | ✅ | case home + durable case workflows |
| Legacy global API/demo | ✅ | still used for benchmark, mock parity, narrated demo |
| Full benchmark | 🔄 | naive baseline checked in; full live run still pending |
| Docs | 🔄 | updated in this pass to match merged reality |
