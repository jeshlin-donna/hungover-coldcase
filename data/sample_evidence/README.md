# Sample Evidence Files — Multi-Format Ingestion Test Set

Synthetic, non-sensitive sample evidence files for manually or automatically testing
every ingestion modality ColdCache supports (`POST /ingest-file`). Five fictional
cases, ~21 files each (105 total), covering all supported formats:

| Format | Extension | Files per case | Ingestion path exercised |
|---|---|---|---|
| Text notes | `.txt` | 6 | plain-text ingestion |
| Photos | `.jpg` | 4 | Claude/Groq vision → forensic description |
| Video clips | `.mp4` | 3 | OpenCV keyframe extraction → vision description |
| Audio | `.wav` | 3 | Whisper / Groq transcription |
| PDF | `.pdf` | 2 | PyMuPDF text extraction |
| CSV | `.csv` | 2 | pandas spreadsheet parsing |
| Excel | `.xlsx` | 1 | pandas spreadsheet parsing |

**Content is authored to feel like real case files**, not placeholder text:
- **Text notes** are full multi-paragraph incident reports, witness statements, detective
  follow-up notes, evidence logs, case summaries, and anonymous tips — with consistent
  names, badge numbers, case numbers, dates, and cross-references between documents.
- **Photos** are detailed synthetic scene renders (gradient sky/lighting, textured
  building facades, forced-entry marks, evidence tent markers, film grain) rather than
  flat text-on-background cards, so vision models have real visual content to describe.
- **Video clips** are CCTV-style renders with timestamp/camera burn-in, film grain, and
  moving person/vehicle silhouettes, exercising real keyframe + vision analysis.
- **Audio** is **real synthesized speech** (macOS `say` + `afconvert`, not sine tones) —
  a witness statement, a 911-style dispatch call, and a detective voice memo per case —
  so Whisper/Groq transcription has actual spoken content to transcribe.

## Cases

1. `case-01-millbrook-heights/` — burglary, suspect Daniel Marsh
2. `case-02-riverside-view/` — burglary, suspect Daniel Marsh (cross-jurisdiction link)
3. `case-03-oakdale-jewelry/` — jewelry store heist, suspect Renata Kovic
4. `case-04-lakeside-arson/` — warehouse arson, suspect Miguel Torres
5. `case-05-harborview-fraud/` — insurance fraud ring, suspect Priya Anand

All content is synthetic/fictional, generated for demo and testing purposes only —
no real people, places, or events.

## Usage

Upload any file through the **Messy Desk** upload panel in the frontend, or directly:

```bash
curl -X POST http://localhost:8000/ingest-file \
  -F "file=@data/sample_evidence/case-01-millbrook-heights/evidence_photo_01.jpg"
```

Audio/video/image files require `LIVE` mode (a working `LLM_API_KEY` in `.env`) to get
real transcription/vision descriptions — in `DEGRADED` mode they still ingest and
return a placeholder description instead of failing.
