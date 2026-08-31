# Understudy — Demo Video Storyboard (~4:00)

Goal: prove **autonomous action** (40%), **architecture** (30%), and **it works on GCP** (30%) in one tight, unedited-feeling take. Two speakers: **Alex** and **Sam** (you + your friend). Keep it live and specific.

## Pre-flight checklist (run before recording)
1. `cd web && npm run emulator` (Firestore emulator, Java on PATH)
2. Seed: `PYTHONPATH=. FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 GOOGLE_CLOUD_PROJECT=demo-understudy python scripts/seed_firestore.py` (for the Commitments board's prior-week data)
3. Agent server: `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 PYTHONPATH=. python scripts/run_server.py` (MOCK_AGENT off if billing is on for the real run; on for a guaranteed-clean take)
4. Dashboard: `cd web && npm run dev:firestore` → open `/meeting`, `/commitments`, `/minutes` in tabs
5. Companion: `cd desktop && npm start` (floats top-right)
6. Slack: `PYTHONPATH=. python scripts/run_slack.py` + the `#under-study` channel visible
7. A slide/webpage to show on screen (for the screen-awareness beat) — e.g., a "Q3 Pricing" slide
8. Have the meeting script (`understudy_agent/fixtures/demo_meeting.txt`) in front of both speakers

## Shot list

| # | Time | On screen | Audio / dialogue | Notes |
|---|---|---|---|---|
| 1 | 0:00–0:18 | Title card → cut to a real video call (Alex + Sam) with the **Companion floating** in the corner | VO: "Every meeting ends with a list of things someone swears they'll do. Most of it quietly rots. Understudy is the teammate that actually does it — while you're still talking." | Hook + problem. Keep it fast. |
| 2 | 0:18–0:35 | The call, Companion visible, "● Understudy · listening" | Alex: "Morning Sam, quick sync." Start the scripted meeting. | Establish the two surfaces exist. |
| 3 | 0:35–2:00 | Companion (and/or dashboard `/meeting`) as they talk | Run the script. As each commitment is spoken, a card appears and flips **queued → running → done**, with the "Why:" reasoning visible. | The core wow. Let 3–4 items land visibly. |
| 4 | 1:15–1:35 | Show a **pricing slide** on screen mid-meeting | Sam references "the pricing deck." Companion shows "Viewing: Q3 pricing slide." | Screen-awareness beat (multimodal Gemini). |
| 5 | 1:35–1:55 | Companion shows the **Acme email → "Needs your OK"** | Alex taps **Approve & send** (in Companion or Slack). Card flips to done. | The one live human-in-the-loop approval. |
| 6 | 2:00–2:35 | Meeting ends → cut to full **dashboard `/meeting`**: all 6 done, real artifacts (draft email, doc, brief). Then `/minutes`. | VO: "By the time they say goodbye, it's done — and here are the minutes, including what was on screen." | Payoff. Open a real artifact. |
| 7 | 2:35–3:10 | **Commitments board** `/commitments` | VO: "But it doesn't stop when the meeting ends. Understudy tracks every commitment for days." Show the overdue item **"Chased 2×"**, the **Slack nudge** that fired, tap **Done** in Slack → board updates. Point at **"14 auto-nudges sent."** | The differentiator — the async follow-through. This is what separates it from every other meeting notetaker. |
| 8 | 3:10–3:40 | **GCP consoles**: Cloud Run (understudy-agent service), Vertex AI logs, Firestore data | VO: "All of it runs on Google Cloud — Gemini 3.5 Flash on Vertex AI, agents built with Google ADK on Cloud Run, state in Firestore, follow-ups on Cloud Scheduler." | Required GCP proof. Show real dashboards. |
| 9 | 3:40–4:00 | Companion + tagline card | VO: "Understudy. It does the work while you talk — and keeps at it until it's done. And your audio never leaves your device." | Close + the privacy angle. |

## Recording tips
- One clean take of the meeting; you can trim between beats but keep the live-execution moment unbroken (that's the credibility).
- Zoom the Companion/dashboard so status pills are legible on a phone screen.
- Keep VO calm and specific — name what's happening ("it categorized that as a calendar event and booked it").
- If running the real Gemini pipeline live, do one rehearsal so latency doesn't surprise you; MOCK_AGENT mode is the safety net for a guaranteed-clean take.
