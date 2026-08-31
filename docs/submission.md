# Understudy — Devpost Submission

## Elevator pitch
**Understudy does the work while you talk — and keeps chasing it until it's done.** A live meeting agent that turns conversation into completed action, in real time, then follows through for days.

## The problem
Every meeting produces commitments — "I'll email the vendor," "someone book the review," "let's file that bug." Then the meeting ends and most of it evaporates: no one writes it down, ownership is fuzzy, and follow-through depends on memory. Existing AI notetakers *transcribe and summarize* — they still leave the actual work, and the chasing, to you.

## What it does
Understudy listens to a meeting in real time and:
1. **Extracts action items as they're spoken**, with the reasoning for each.
2. **Executes everything it safely can, in parallel, while the meeting is still going** — drafts the email, writes the doc, books the review, posts to Slack, files the ticket.
3. **Waits for one-tap approval** on anything irreversible (like actually sending an email).
4. **Watches the shared screen** (with permission) to understand slides/docs/sites, and generates **meeting minutes** that include what was actually shown.
5. **Keeps working after the meeting** — a background scanner tracks every commitment across days, nudges owners in Slack, escalates what stalls, and auto-closes items when someone says they're done.

Two surfaces: a **floating Companion** widget that sits over your meeting, and a **web dashboard** (live meeting view + a standing Commitments board + Minutes).

## Value proposition
It collapses the gap between *deciding* to do something in a meeting and it *being done*. The reversible work is finished before the meeting ends; the rest is tracked to completion automatically. It's the difference between a notetaker and a teammate.

## How it works (architecture)
See `docs/architecture.png`.
- **On-device:** a local listener captures the mic, segments speech with VAD, and transcribes with **faster-whisper**. Audio never leaves the device — only transcript text is sent onward. A screen-watcher captures changed frames (perceptual-hash dedup) for multimodal understanding.
- **Cloud Run — Agent backend (Google ADK):** a **watcher** agent turns transcript into structured action items; an **orchestrator** (`ParallelAgent`) fans them out to **tool agents** running concurrently; each result is persisted to Firestore as it progresses.
- **Firestore:** the commitment ledger + live meeting state; the frontend reads it in real time via `onSnapshot`.
- **Cloud Scheduler → follow-up scanner:** finds overdue commitments and nudges owners in Slack.
- **Model:** every reasoning and generation step is **Gemini 3.5 Flash via Vertex AI** (multimodal for screen understanding).

## Technologies used
- **Gemini 3.5 Flash** (Vertex AI) — extraction, tool content generation, multimodal screen analysis, minutes.
- **Google Agent Development Kit (ADK)** — `LlmAgent` with structured output, `ParallelAgent` fan-out, sessions/state.
- **Google Cloud:** Cloud Run (agent backend), Firestore (ledger + realtime), Cloud Scheduler (follow-up automation).
- **faster-whisper + webrtcvad + sounddevice** — on-device transcription.
- **Slack (Bolt for Python)** — live feed, approvals, and follow-up nudges with interactive buttons.
- **Vite + React + TypeScript** — dashboard + companion; Firestore Web SDK `onSnapshot` for realtime.
- **Electron** — the always-on-top companion window.

## Other data sources
- Live microphone audio (on-device transcription).
- Shared-screen frames (opt-in, permission-gated, downscaled, only *changed* frames sent to Gemini).
- The team's Slack workspace (for feed, approvals, nudges, assignment).

## How we built it
Designed the product and UI directions first (dark-restrained "Sage" system), then built in **Antigravity** with the agent brain, the on-device listener, a Firestore-backed ledger (developed against the local emulator), Slack integration in Socket Mode, and a FastAPI server that unifies everything into one live pipeline. A `MOCK_AGENT` mode lets the entire flow run with zero model calls for fast, deterministic testing and demos.

## Findings & learnings
- **Local transcription beats cloud STT for this use case:** running whisper on-device removed the hardest infrastructure risk (streaming caps, reconnects, cold starts), improved demo reliability, and gave us a genuine privacy story — audio never leaves the device.
- **Debounce Gemini on finalized utterances, not interim ones** — controls cost and latency in a live loop.
- **A subscription seam (`subscribeToMeeting`/`subscribeToCommitments`) paid off:** we built the whole UI on a mock store, then swapped to Firestore `onSnapshot` behind the same interface with a one-line change.
- **The differentiator isn't the live moment — it's the follow-through.** "Meeting → action items" is a crowded space; the async commitment ledger that chases work for days is what makes Understudy feel like a teammate.
- **Human-in-the-loop, scoped by reversibility,** is the right autonomy default: auto-do the reversible, ask once for the irreversible.

## Challenges
- Free-tier model quotas throttled iterative development — solved by moving to billing/Vertex and building a `MOCK_AGENT` path so most work needed no live calls.
- Real-time utterance segmentation in noisy rooms — solved with VAD + a worker-thread transcription queue so capture never blocks.

## Requirements checklist
- **Gemini 3.5+:** `gemini-3.5-flash` via Vertex AI (and Gemini API for local dev). ✅
- **A Google agent framework:** Google ADK (`LlmAgent`, `ParallelAgent`). ✅
- **A Google Cloud service:** Cloud Run + Firestore + Cloud Scheduler. ✅

## What's next
- Real Gmail/Calendar/Docs delivery via OAuth (currently drafts, approve-to-send).
- Confidence-gated proactive clarification (ask when unsure, act when confident).
- Model Armor guardrails + OpenTelemetry reasoning-chain audit view for enterprise readiness.
