# Synopsis — MindEase
## AI-Powered Mental Wellness Web Application

**Project Type**: Minor Project  
**Technology Domain**: Artificial Intelligence / Full-Stack Web Development  
**Academic Year**: 2025–2026

---

## Abstract

MindEase is an AI-powered mental wellness web application designed to bridge the gap between untreated psychological distress and formal clinical intervention. Targeting individuals experiencing mild-to-moderate anxiety, ADHD, and stress, the platform provides personalised cognitive behavioural therapy (CBT) sessions powered by Google Gemini Flash, speech-based journaling with acoustic emotion recognition, and an automated therapist recommendation engine. The system is built on a Python FastAPI backend, Supabase PostgreSQL database with Row Level Security, and a fully responsive web frontend with adaptive theming.

---

## Problem Statement

India carries a disproportionate burden of global mental health conditions — psychiatric disorders are the second leading cause of Years Lived with Disability. Despite high prevalence, a large majority of individuals experiencing distress never access formal care due to cost, stigma, geographic barriers, and long wait times for clinical appointments. Existing digital tools either lack clinical structure or feel impersonal and generic.

---

## Objectives

1. Build an accessible, stigma-free digital space for users to articulate and process psychological distress
2. Implement structured AI-guided cognitive therapy sessions using condition-aware Gemini prompt engineering
3. Provide acoustic emotion recognition to detect emotional states beyond what users consciously express
4. Automate therapist matching based on diagnosis and geographic proximity
5. Generate clinical summary PDFs to reduce intake time when users transition to professional care
6. Maintain a robust safety layer for crisis escalation aligned with Tele-MANAS (India's national tele-mental health programme)

---

## Technical Architecture

### Frontend
- Single-page responsive web application (HTML5, CSS3, Vanilla JS)
- 5-palette adaptive theming via CSS custom properties
- Minimalist Panic Mode with 4-4-4 breathing exercise
- Web Audio API for browser-native voice recording

### Backend
- Python FastAPI REST API deployed on Google Cloud Platform
- 9 API endpoints covering: diagnosis, session lifecycle, mood logging, voice processing, therapist search, PDF generation, crisis alerts
- Stateless Gemini session reconstruction via conversation history

### AI Layer
- Google Gemini 1.5 Flash with 4-layer custom prompt engineering
- 4 therapeutic session modes: Empathic Listener, Socratic Inquiry, Grounding Exercise, CBT Challenge
- Condition-specific prompt overlays for anxiety, ADHD, stress, sleep
- Separate Gemini call for session insight extraction in first-person journal style
- OpenAI Whisper for speech-to-text transcription
- Acoustic emotion analysis (calm / anxious / fatigue / sad vector)

### Database
- Supabase PostgreSQL with Row Level Security on all 5 tables
- Tables: profiles, diagnoses, sessions, mood_logs, exercises
- JWT-based authentication; security enforced at the database layer

### Additional Systems
- Python web scraper (BeautifulSoup + Playwright) for therapist discovery
- ReportLab PDF generation for clinical referral documents
- Twilio + SendGrid integration for crisis emergency contact alerts
- Keyword + Gemini intent classifier crisis guardrail layer

---

## Key Features

| Feature | Technical Components |
|---|---|
| Adaptive UI Theming | CSS custom properties, 5 palettes, panic mode overlay |
| Voice Journaling + SER | Web Audio API, Whisper STT, Gemini emotion classification |
| AI Therapy Sessions | Gemini Flash, 4-layer prompt stack, 4 therapeutic modes |
| Mood & Streak Tracking | Supabase mood_logs, habit checklist, 7-day streak display |
| Therapist Finder | BeautifulSoup + Playwright scraper, rating filter, map integration |
| Clinical PDF Report | ReportLab, aggregated insights (no raw chat exposed) |
| Crisis Escalation Engine | Keyword scan + Gemini intent classifier, Tele-MANAS integration |

---

## Tools & Technologies

Python 3.11 · FastAPI · Google Gemini 1.5 Flash · OpenAI Whisper · Supabase · PostgreSQL · ReportLab · BeautifulSoup4 · Playwright · Twilio · SendGrid · HTML5 · CSS3 · JavaScript · Google Cloud Platform

---

## Expected Outcomes

1. A fully functional web application accessible on desktop and mobile
2. End-to-end AI therapy session flow with 4 distinct modes
3. Demonstrated crisis safety layer with Tele-MANAS integration
4. Automated therapist recommendation pipeline
5. One-click clinical PDF report generation
6. Complete technical documentation (README, API reference, system prompt documentation)

---

## References

1. National Tele Mental Health Programme — Tele MANAS Operational Guidelines, MoHFW, 2022
2. Google Gemini API Documentation — generativelanguage.googleapis.com
3. Supabase Row Level Security Documentation — supabase.com/docs
4. Beck, A.T. — Cognitive Therapy and the Emotional Disorders, 1976
5. PIB — Tele MANAS: Revolutionizing Mental Health Care in India, April 2025
