# MindEase — Project Bible

> **College Minor Project · Aug 2026**  
> A full-stack AI-powered mental wellness web application targeting mild-to-moderate anxiety, ADHD, and daily stress. Built with Gemini Flash, FastAPI, Supabase, and a responsive web frontend.

---

## Table of Contents

1. [What is MindEase?](#1-what-is-mindease)
2. [What We Are Building](#2-what-we-are-building)
3. [Feature Catalogue](#3-feature-catalogue)
4. [Tech Stack](#4-tech-stack)
5. [Folder Structure](#5-folder-structure)
6. [Database Schema](#6-database-schema)
7. [Backend API Reference](#7-backend-api-reference)
8. [Gemini AI Architecture](#8-gemini-ai-architecture)
9. [Frontend Architecture](#9-frontend-architecture)
10. [User Flow & Workflow](#10-user-flow--workflow)
11. [Security & Safety Layer](#11-security--safety-layer)
12. [Build Timeline](#12-build-timeline)
13. [Environment Variables](#13-environment-variables)
14. [Running Locally](#14-running-locally)

---

## 1. What is MindEase?

MindEase is a **fully customisable AI mental wellness platform** designed for people experiencing mild-to-moderate anxiety, ADHD, and everyday stress. It is not a crisis service and does not attempt to treat clinical depression or severe psychiatric conditions — for those, it refers users to Tele-MANAS (14416) or matched local therapists.

The core thesis: most people who need support never access it because real therapy is expensive, inaccessible, or stigmatised. MindEase gives them a private, judgment-free space to:

- Talk freely (voice or text, no word limit)
- Work through structured cognitive therapy with an AI that feels human, not clinical
- Track their mood and mental patterns over time
- Find and prepare for real therapist appointments when they're ready

The AI persona is warm, direct, and uses Hinglish naturally — built around a real conversational style that feels like a close friend who genuinely listens, not a help desk bot.

---

## 2. What We Are Building

| Layer | What it is |
|---|---|
| **Web App** | Responsive HTML/CSS/JS frontend (no framework — pure vanilla for deadline speed); renders perfectly on desktop and mobile |
| **FastAPI Backend** | Python REST API on GCP VM; handles auth, session logic, Gemini wrapper calls, PDF generation, therapist scraping |
| **Gemini Flash Wrapper** | Custom prompt engineering layer on top of Gemini 1.5 Flash; 4 distinct therapeutic modes with condition-specific overlays |
| **Supabase** | PostgreSQL DB with Row Level Security; Auth (JWT); real-time subscriptions for live session sync |
| **Scraper Engine** | Python (BeautifulSoup + Playwright) scraper that pulls local therapist data at session end, filtered by specialty and rating |
| **PDF Generator** | ReportLab-based clinical summary PDF for therapist referrals — no raw chat exposed |

### What it is NOT

- Not a React Native mobile app (web-first for the deadline; mobile-responsive is sufficient)
- Not a crisis helpline (safety layer redirects to Tele-MANAS 14416)
- Not a replacement for clinical psychiatry

---

## 3. Feature Catalogue

### Core Features

#### F1 — Pre-Registration Assessment
Before creating an account, the user answers 3 baseline questions:
- When do you feel lowest during the day?
- What kind of thoughts repeat most often?
- What have you tried before that helped, even a little?

These answers generate an **initial diagnosis** (anxiety / adhd / stress / sleep) and severity score (1–10), stored in Supabase. This diagnosis shapes every subsequent session, therapist match, and PDF report.

#### F2 — Account & Progress Persistence
Users sign up (email + password via Supabase Auth) to save:
- Diagnosis history
- Session logs and insights
- Mood trend data
- Habit streaks

A guest can complete the assessment and one session, but saving requires an account. The upsell moment is natural: "Your session insight is ready — save it to your profile."

#### F3 — Fully Customisable UI (Adaptive Themes)
During onboarding, users pick 1 of 5 colour palettes they find calming:
- Teal (default)
- Rose / Pink
- Sage / Green
- Sky / Blue
- Sand / Warm

CSS custom properties (`--c-primary`, `--c-accent`, `--c-warm`) are swapped body-class-wide. The entire UI — cards, buttons, charts, orb, nav — re-renders in the chosen palette.

**Contextual Panic Transition**: When the AI detects high-anxiety language in a session (via Gemini's response metadata or keyword flags), it can trigger a soft UI transition: reduced animations, lower contrast, ambient audio option.

#### F4 — Voice Journaling + Speech Emotion Recognition (SER)
- **Speech-to-Text**: Web Audio API → Whisper API (or Google Speech-to-Text) transcribes the user's voice in real time, no word limit.
- **Acoustic Emotion Analysis**: Pitch, volume, pause frequency, and speech rate are analysed to detect fatigue, anxiety, and emotional valence — independent of what the words say.
- Output: a `{ calm: 72%, anxious: 24%, fatigue: 18% }` vector that gets prepended to the Gemini session context, so the AI knows the emotional state behind the words.

> Example: User says "I'm fine, just tired" but the voice analysis shows 68% anxiety and long pauses → Gemini probes deeper instead of accepting the surface answer.

#### F5 — AI Therapy Sessions (Gemini Flash + Custom Wrappers)

**Session Modes** (user-selectable before starting):

| Mode | What the AI does |
|---|---|
| 🤝 Empathic Listener | Listens and validates. No unsolicited advice. Reflects feelings back. |
| 🔍 Socratic Inquiry | Asks structured questions that guide the user to their own answers. Never hands over conclusions. |
| 🌿 Grounding Exercise | Pauses conversation, runs a sensory grounding technique (5-4-3-2-1, box breathing, body scan) with screen micro-interactions. |
| 🧩 CBT Challenge | Identifies cognitive distortions in real time (catastrophizing, mind-reading, all-or-nothing). Walks through a thought record. |

**Session Arc** (all modes follow this silently):
1. **Open** — warm, single opening question
2. **Explore** — 2–4 Socratic probes to reach the root thought
3. **Challenge** — surface the distortion without naming it clinically
4. **Reframe** — user arrives at the insight themselves
5. **Close** — AI summarises in 1–2 lines; saves as session insight

**Condition-Specific Overlays**: The system prompt changes based on diagnosis. Anxiety gets distortion-spotting and probability challenges. ADHD gets shorter messages, no productivity moralizing, micro-win reinforcement. Stress gets problem vs. feeling triage. Sleep gets rumination loop interruption.

**Session ends when the user decides** — no forced time limit. They tap "End Session", see a mood-after slider, and get their insight card.

#### F6 — Mood Tracking & Progress Chart
- Daily mood check-in (5 emoji scale, 1–5)
- 7-day and 30-day mood trend chart
- Session history with insights shown chronologically
- Condition chip on each entry (anxiety / stress / adhd)

#### F7 — Streak & Habit Tracker
Three daily habits to check off:
- Morning check-in (mood log)
- Voice journal or session
- Breathing/grounding exercise

Consecutive days of completing all three = streak. Displayed with flame icon and 7-day dot row. ADHD users especially benefit from this visible loop — small wins, visible progress.

Missing a day resets the streak to 0. The AI references streak data naturally in sessions ("you've been consistent this week — that matters").

#### F8 — Therapist Finder (Scraper + Map)
At session end, or from the dashboard, the user can request therapist recommendations.

**Backend flow**:
1. Fetch user's latest diagnosis from Supabase
2. Run Python scraper (BeautifulSoup + Playwright) against Practo, JustDial, and Google Maps results for the user's city
3. Filter by: specialty matching diagnosis, minimum 4.5 Google rating, active/verified profile
4. Return top 3–5 results with: name, specialty, location coordinates, charges, contact
5. Display on OpenStreetMap/Mapbox with clinic pins

**Data returned per therapist**:
- Name, qualifications
- Specialties (matched to diagnosis)
- Google rating
- Clinic address + lat/lng
- Session charges
- Phone / booking link

#### F9 — AI Clinical Summary PDF (Therapist Referral Report)
One-click PDF generated by ReportLab:

**Contents**:
- Patient name, age, date of report
- Diagnosed condition + severity score
- Assessment Q&A summary (baseline questions)
- Mood trend graph (last 30 days)
- Top recurring themes/triggers (extracted by Gemini from session patterns — no raw chat)
- Session count and consistency
- Key insights from sessions (in user's own words)
- Referral note: "Patient self-referred for professional support"

**What it does NOT include**: raw chat transcripts, private voice journal content.

**Benefit**: saves 15–20 minutes of diagnostic intake for the therapist.

#### F10 — Safety & Crisis Escalation Engine
Always-on guardrail layer, runs parallel to every session.

**Detection**:
- Regex keyword scan on every user message (self-harm vocabulary list)
- Gemini intent classifier — if the model's confidence of crisis intent exceeds threshold, it flags the session
- SER fatigue + distress combination above a threshold also triggers soft escalation

**Response**:
1. AI chat pauses immediately
2. Crisis banner pops up full-screen: "We noticed something. You don't have to face this alone."
3. One-tap buttons: Tele-MANAS (14416), iCall (9152987821), Vandrevala Foundation
4. Option: "Alert my emergency contact" — sends SMS/email via Twilio/SendGrid to a pre-saved contact

**The 🌬️ Panic Button** (always visible, bottom-right):
- Any user can tap it at any time
- Instantly enters Minimalist Panic Mode: all UI hides, animated breathing orb appears
- 4-4-4 breathing exercise (Breathe in 4s → Hold 4s → Breathe out 4s) with live countdown
- "I'm okay, go back" exits Panic Mode

---

## 4. Tech Stack

### Frontend
| Tool | Purpose |
|---|---|
| HTML5 / CSS3 / Vanilla JS | No framework overhead; fastest to ship; works everywhere |
| CSS Custom Properties | Theme switching across 5 palettes without JS re-renders |
| Web Audio API | Browser-native voice recording |
| Google Fonts (DM Serif Display + Inter + JetBrains Mono) | Typography system |
| OpenStreetMap / Mapbox GL JS | Therapist location map |

### Backend
| Tool | Purpose |
|---|---|
| Python 3.11 | Primary backend language |
| FastAPI | REST API framework; async; OpenAPI docs auto-generated |
| `google-generativeai` SDK | Gemini 1.5 Flash API calls |
| `supabase-py` | Supabase DB + Auth client |
| BeautifulSoup4 + Playwright | Therapist web scraper |
| ReportLab | PDF generation for clinical summary |
| Twilio / SendGrid | SMS + email for emergency contact alerts |
| Whisper API (OpenAI) | Speech-to-text transcription |
| Uvicorn | ASGI server |

### Infrastructure
| Tool | Purpose |
|---|---|
| GCP VM (e2-micro or e2-small) | FastAPI hosting |
| Supabase | PostgreSQL + Auth + Row Level Security + Realtime |
| GitHub | Version control |

### Why these choices
- **Gemini Flash over GPT-4o**: lower cost per token, faster response, generous free tier — critical for a college project that needs to demo live
- **Supabase over Firebase**: SQL is easier to query for analytics; RLS is more expressive than Firestore rules; built-in Auth
- **Vanilla JS over React**: deadline is Aug 9; no build pipeline to configure; the UI is not component-heavy enough to justify the overhead
- **FastAPI over Flask**: async by default; Pydantic validation; auto-generated docs useful for evaluators

---

## 5. Folder Structure

```
mindease/
│
├── backend/                        # FastAPI application
│   ├── main.py                     # All API routes (auth, sessions, mood, diagnosis)
│   ├── gemini_system_prompt.py     # Prompt builder — base persona + condition overlays
│   ├── gemini_modes.py             # 4 therapeutic mode prompt fragments
│   ├── scraper.py                  # Therapist scraper (BeautifulSoup + Playwright)
│   ├── pdf_generator.py            # ReportLab clinical summary PDF
│   ├── crisis_guardrail.py         # Keyword scanner + intent classifier
│   ├── ser_analysis.py             # Speech emotion recognition processing
│   ├── requirements.txt            # All Python dependencies
│   └── .env                        # Secrets (never commit)
│
├── frontend/                       # Web application
│   ├── index.html                  # Single-file app (landing + onboarding + dashboard)
│   ├── assets/
│   │   ├── audio/                  # Ambient sounds (rain, white noise) for calm mode
│   │   └── icons/                  # SVG icons
│   └── sw.js                       # Service worker for offline fallback
│
├── db/
│   └── schema.sql                  # Full Supabase schema + RLS policies
│
├── docs/
│   ├── API.md                      # Detailed API endpoint docs
│   ├── SYSTEM_PROMPT.md            # Documented Gemini prompt architecture
│   └── SYNOPSIS.md                 # College synopsis document
│
└── scripts/
    ├── seed_db.py                  # Seed fake data for demo
    └── test_session.py             # End-to-end session smoke test
```

---

## 6. Database Schema

```sql
-- Five tables, all with Row Level Security enabled

profiles       (id, name, created_at)
               → auto-created on signup via Supabase trigger

diagnoses      (id, user_id, condition, severity_score, answers_json, created_at)
               → condition: anxiety | adhd | stress | sleep
               → severity_score: 1–10
               → answers_json: raw assessment Q&A

sessions       (id, user_id, diagnosis_id, chat_log_json, insight,
                mood_before, mood_after, created_at, ended_at)
               → insight: AI-generated 1–2 line summary = the "cure" saved to chart
               → ended_at NULL = session still active

mood_logs      (id, user_id, score, note, logged_at)
               → score: 1–5

exercises      (id, user_id, type, duration_secs, completed_at)
               → type: breathing | thought_journal | grounding | focus_timer
```

**RLS rules**: every table enforces `auth.uid() = user_id` — no user can read or write another user's data, even if an API endpoint is misconfigured. Security lives at the database layer, not the API layer.

---

## 7. Backend API Reference

### Auth
Handled entirely by Supabase client-side. The FastAPI backend validates the JWT on every request via `supabase.auth.get_user(token)`.

### Endpoints

```
POST   /api/v1/diagnosis              Save assessment result
GET    /api/v1/diagnosis/latest       Get user's current diagnosis

POST   /api/v1/session/start          Create session + get AI opening message
POST   /api/v1/session/message        Send message → get AI reply
POST   /api/v1/session/end            End session → generate + save insight
GET    /api/v1/session/history        Past sessions with insights (progress chart)

POST   /api/v1/mood                   Log daily mood
GET    /api/v1/mood/history           Mood trend (last N days)

POST   /api/v1/voice/transcribe       Upload audio → get transcript + SER scores
POST   /api/v1/therapist/search       Trigger scraper → return matched therapists
POST   /api/v1/report/generate        Generate + return clinical summary PDF
POST   /api/v1/crisis/alert           Send emergency contact SMS/email
```

---

## 8. Gemini AI Architecture

### How the wrapper works

Every session call to Gemini is **stateless** — the API has no memory between calls. We maintain the full conversation history client-side and send it with every request. The backend reconstructs the Gemini `ChatSession` from the history array on each call.

```python
# History format (Gemini SDK)
history = [
    {"role": "user",  "parts": ["I've been really anxious lately"]},
    {"role": "model", "parts": ["What's the thing you keep coming back to most?"]},
]

# Each request: rebuild chat + send new message
model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt)
chat  = model.start_chat(history=history)
reply = chat.send_message(new_user_message)
```

### System prompt layers (built by `gemini_system_prompt.py`)

```
Layer 1: Base Persona
  → Who MindEase is, tone rules, style rules, what to never say
  → Session arc: Open → Explore → Challenge → Reframe → Close

Layer 2: Past Insights Block
  → Last 5 session insights pulled from DB
  → Referenced naturally if relevant ("you mentioned last week...")

Layer 3: Condition Overlay
  → Anxiety: distortion types to watch, reframe angles, short responses
  → ADHD: follow the thread, no moralizing, micro-wins, emotional flooding
  → Stress: problem vs feeling triage, locus of control, priority framing
  → Sleep: rumination loop interruption, sleep pressure paradox, body trust

Layer 4: Mode Fragment (injected at session start based on user selection)
  → Empathic Listener: validation-first, no advice
  → Socratic Inquiry: question-only, never hand conclusions
  → Grounding Exercise: pause conversation, run technique
  → CBT Challenge: name distortions, thought records, evidence checking
```

### Session insight extraction

At `POST /session/end`, a separate Gemini call reads the full chat log and extracts the core insight in first-person:

```python
prompt = f"""
Extract the single most important insight the user arrived at.
Write it in first person, 1-2 sentences, like a journal entry.
No therapy-speak. No "The user realized..." — write AS them.

Conversation:
{convo_text}

Insight:
"""
```

This becomes the `sessions.insight` field — the "cure" saved to the chart.

---

## 9. Frontend Architecture

### Single-file app structure

`index.html` contains four pages as `<div class="page">` blocks:
- `page-landing` — public landing, feature showcase, assessment teaser
- `page-onboarding` — theme picker (shown after "Get Started")
- `page-dashboard` — full authenticated experience
- `page-panic` — minimalist breathing screen (overlays everything)

Page routing is pure JS (`showPage(name)` function swaps `display`). No router library needed.

### Theme system

Five palettes, applied as body classes:
```css
body              → Teal (default)
body.theme-pink   → Rose
body.theme-sage   → Sage
body.theme-sky    → Sky
body.theme-sand   → Sand
```

All colours reference `var(--c-primary)`, `var(--c-accent)`, `var(--c-warm)`. Swapping the body class is the entire theme change — zero JS re-renders.

### Key UI components

| Component | Where |
|---|---|
| Breathing Orb | Landing hero — CSS radial gradient, `orb-breathe` keyframe animation |
| Panic Button | Fixed bottom-right, always visible, triggers Panic Mode |
| Panic Mode | Full-screen minimalist overlay, 4-4-4 breathing countdown |
| Mode Switcher | 4-tab selector before session start, updates description + tags |
| Streak Tracker | 7-dot week row + 3 daily habit checkboxes |
| Voice Recorder | Mic button → waveform animation → SER reading |
| Mood Chart | 7 CSS flexbox bars, proportional heights |
| Insight List | Chronological session insights with condition chips |
| Therapist Cards | Avatar + name + specialty tags + rating + map placeholder |
| Crisis Banner | Hidden by default, revealed by safety layer trigger |

---

## 10. User Flow & Workflow

```
FIRST VISIT (no account)
    │
    ▼
Landing Page
  • Hero + breathing orb
  • Feature overview
  • Assessment teaser (Q1 of 3 interactive)
    │
    ▼
Assessment (3 questions, no login required)
  • Answers → diagnosis + severity score
  • Stored in localStorage until account created
    │
    ▼
Onboarding — Theme Picker
  • Pick colour palette
  • CSS body class applied
    │
    ▼
Signup / Login (Supabase Auth)
  • Assessment answers migrated from localStorage → Supabase
    │
    ▼
Dashboard
    │
    ├── Daily mood check-in (emoji 1–5)
    │
    ├── Start Session
    │     ├── Pick mode (Empathic / Socratic / Grounding / CBT)
    │     ├── Mood-before slider (1–5)
    │     ├── Chat or Voice session
    │     │     └── [Safety layer running in parallel on every message]
    │     ├── Mood-after slider
    │     └── Session insight generated + saved → appears in Progress
    │
    ├── Voice Journal
    │     ├── Record → transcribe → SER analysis
    │     └── Transcript sent to Gemini as session context
    │
    ├── Find Therapist
    │     ├── Scraper runs with diagnosis
    │     ├── Returns 3–5 matched therapists
    │     └── Map view with clinic pins
    │
    ├── My Report
    │     └── Generate clinical summary PDF
    │
    ├── Progress
    │     ├── 7-day / 30-day mood chart
    │     └── Past session insights (the "cure chart")
    │
    └── [🌬️ Panic Button — always accessible]
          └── Panic Mode: minimalist breathing overlay
                └── "I'm okay" → returns to previous screen
```

---

## 11. Security & Safety Layer

### Data security

- All DB tables have RLS enabled — `auth.uid() = user_id` enforced at Postgres level
- FastAPI validates Supabase JWT on every request
- No raw chat logs are included in the PDF report
- Voice recordings are processed and discarded — not stored

### Crisis guardrail (always-on)

```python
# crisis_guardrail.py — runs on every user message

CRISIS_KEYWORDS = [
    "kill myself", "end it", "don't want to be here",
    "self harm", "cutting", "suicide", "worthless",
    "no point", "can't go on", "disappear forever"
    # + 40 more in English and Hindi/Hinglish
]

def check_message(text: str) -> dict:
    # Layer 1: fast keyword scan
    for kw in CRISIS_KEYWORDS:
        if kw in text.lower():
            return {"crisis": True, "method": "keyword"}

    # Layer 2: Gemini intent classification
    result = gemini.generate_content(
        f"Does this message express suicidal ideation or intent to self-harm? "
        f"Answer only YES or NO.\n\nMessage: {text}"
    )
    if result.text.strip().upper() == "YES":
        return {"crisis": True, "method": "llm"}

    return {"crisis": False}
```

When `crisis: True`:
1. `/session/message` returns a `crisis_detected: true` flag alongside the reply
2. Frontend shows crisis banner immediately, pauses chat input
3. If emergency contact is saved, option to trigger SMS alert

---

## 12. Build Timeline

| Date | Deliverable |
|---|---|
| Aug 4 (today) | Schema SQL in Supabase ✓, FastAPI skeleton ✓, UI prototype ✓ |
| Aug 5 | Landing page finalised, assessment flow wired to backend |
| Aug 6 | Auth (Supabase), dashboard, mood log, habit tracker |
| Aug 7 | Chat screen wired to Gemini, all 4 modes working, crisis layer |
| Aug 8 | Voice journal, SER, therapist scraper, PDF generator |
| Aug 9 | Documentation, synopsis, demo recording, final polish |

---

## 13. Environment Variables

```bash
# backend/.env

GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key      # server-side only
SUPABASE_ANON_KEY=your_anon_key                 # also used client-side

OPENAI_API_KEY=your_openai_key                  # for Whisper STT

TWILIO_ACCOUNT_SID=your_twilio_sid              # for crisis SMS
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+1xxxxxxxxxx

SENDGRID_API_KEY=your_sendgrid_key              # for crisis email

MAPBOX_TOKEN=your_mapbox_token                  # for map tiles
```

---

## 14. Running Locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the API
uvicorn main:app --reload --port 8000

# API docs auto-available at:
# http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
# No build step needed — open directly
open index.html
# or serve with:
python -m http.server 3000
```

### Database

1. Go to your Supabase project → SQL Editor
2. Paste and run `db/schema.sql`
3. Enable email auth in Supabase Auth settings
4. Copy `SUPABASE_URL` and `SUPABASE_ANON_KEY` into `frontend/index.html` (or a config file)

### Seeding demo data

```bash
cd scripts
python seed_db.py
# Seeds: 1 test user, 4 sessions with insights, 14 days of mood logs
```

---

## Appendix — Tele-MANAS Reference

MindEase is built with Tele-MANAS awareness baked in. The safety layer always surfaces the national helpline (14416) before any third-party service. For academic context: Tele-MANAS is the Government of India's National Tele Mental Health Programme, launched October 2022, operating across 53 state cells in 20 languages, having handled 2M+ calls by April 2025. MindEase is designed to complement — not compete with — this infrastructure by serving the pre-clinical population who need support but are not yet in crisis.

---

*Built by Arav Misra & team · Secured Systems Technologies Pvt. Ltd. · BCA Minor Project 2026*