# MindEase — Gemini Prompt Architecture

## Overview

The MindEase AI is built as a **4-layer prompt stack** assembled at session start.
Each layer is independent — changing one doesn't affect the others.

```
┌─────────────────────────────────────────┐
│  Layer 4: Therapeutic Mode Fragment     │  ← user selects at session start
│  (empathic / socratic / grounding / cbt)│
├─────────────────────────────────────────┤
│  Layer 3: Condition Overlay             │  ← from user's diagnosis
│  (anxiety / adhd / stress / sleep)      │
├─────────────────────────────────────────┤
│  Layer 2: Past Insights Block           │  ← from DB (last 5 sessions)
│  "You mentioned last week..."           │
├─────────────────────────────────────────┤
│  Layer 1: Base Persona                  │  ← always present
│  Who MindEase is, tone rules, arc       │
└─────────────────────────────────────────┘
```

## Layer 1: Base Persona
- Identity: warm, direct close friend — not a therapist, not a bot
- Tone rules: short responses (1–3 sentences), no therapy-speak, Hinglish OK
- Session arc (silent): Open → Explore → Challenge → Reframe → Close
- Hard rules: never say "I hear you that sounds really hard", never lecture
- Crisis escalation: always refer to Tele-MANAS 14416

## Layer 2: Past Insights
Pulled from `sessions.insight` (last 5 completed sessions).
Referenced naturally if the conversation connects to a past theme.

## Layer 3: Condition Overlays
| Condition | Key distortions | Reframe angles |
|---|---|---|
| Anxiety | Catastrophizing, mind-reading, fortune-telling | Probability, evidence, decatastrophizing |
| ADHD | Task paralysis, rejection sensitivity | Micro-wins, body-doubling, no moralizing |
| Stress | Problem vs feeling confusion | Locus of control, priority framing |
| Sleep | Rumination loops, sleep pressure | Externalize thoughts, body trust |

## Layer 4: Mode Fragments
| Mode | Behaviour |
|---|---|
| Empathic Listener | Validate only, no advice, reflect and ask one question |
| Socratic Inquiry | Question-only, never hand conclusions, go progressively deeper |
| Grounding Exercise | Pause conversation, run 5-4-3-2-1 / box breathing / body scan |
| CBT Challenge | Identify distortions, thought record, evidence checking |

## Session History (stateless Gemini)
Gemini has no memory between API calls.
History is maintained client-side and passed on every request:
```json
history: [
  {"role": "user",  "parts": ["I'm really anxious about my exams"]},
  {"role": "model", "parts": ["What's the part that bothers you most?"]}
]
```
Backend reconstructs `ChatSession` from history on every call.

## Insight Extraction
A separate Gemini call at `POST /session/end` reads the full chat log
and extracts the core insight in first-person, journal-style language.
This is the "cure" saved to the user's chart.
