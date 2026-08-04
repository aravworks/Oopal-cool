# MindEase — API Reference

Base URL: `http://your-gcp-vm-ip:8000`  
Auth: All routes except `/health` require `Authorization: Bearer <supabase_jwt>`

---

## Health
`GET /health` → `{ status, service }`

---

## Diagnosis
`POST /api/v1/diagnosis`  
Body: `{ condition, severity_score, answers_json }`  
Returns: `{ diagnosis_id, condition }`

`GET /api/v1/diagnosis/latest`  
Returns: `{ diagnosis }` (full row or null)

---

## Sessions
`POST /api/v1/session/start`  
Body: `{ diagnosis_id }`  
Returns: `{ session_id, condition, opening_message }`

`POST /api/v1/session/message`  
Body: `{ session_id, message, history: [{role, parts:[text]}] }`  
Returns: `{ reply }` — also checks crisis guardrail; returns `crisis_detected: true` if triggered

`POST /api/v1/session/end`  
Body: `{ session_id, mood_before, mood_after, history }`  
Returns: `{ session_id, insight, mood_delta }`

`GET /api/v1/session/history?limit=20`  
Returns: `{ sessions: [...] }`

---

## Mood
`POST /api/v1/mood`  
Body: `{ score: 1–5, note: "" }`  
Returns: `{ logged, mood_id }`

`GET /api/v1/mood/history?days=30`  
Returns: `{ mood_history: [{score, note, logged_at}] }`

---

## Voice
`POST /api/v1/voice/transcribe`  
Body: multipart form — `audio` file field  
Returns: `{ transcript, duration_secs, language, emotion: {calm, anxious, fatigue, ...}, context_for_gemini }`

---

## Therapist Finder
`POST /api/v1/therapist/search`  
Body: `{ city, condition }` (condition defaults to user's latest diagnosis)  
Returns: `{ therapists: [{name, specialty, rating, fee, location, tags, ...}] }`

---

## Report
`POST /api/v1/report/generate`  
Returns: PDF bytes (`Content-Type: application/pdf`)

---

## Crisis
`POST /api/v1/crisis/alert`  
Body: `{ contact_name, contact_phone, contact_email }`  
Returns: `{ sms: {sent, ...}, email: {sent, ...} }`

---

## Error format
All errors: `{ error: "message" }` with appropriate HTTP status code.
