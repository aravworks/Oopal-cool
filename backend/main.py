"""
MindEase Backend — FastAPI  (fully wired)
All routes active. All modules imported and called.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import google.generativeai as genai
import os, json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ── local modules ─────────────────────────────────────────
from gemini_system_prompt import build_system_prompt, get_time_context, generate_with_fallback, GEMINI_CALL_TIMEOUT
from gemini_modes        import get_mode_prompt
from crisis_guardrail    import check_message, send_emergency_alert
from ser_analysis        import process_voice_input
from scraper             import find_therapists
from pdf_generator       import generate_pdf

# ── app ───────────────────────────────────────────────────
app = FastAPI(title="MindEase API", version="1.1.0")

ALLOWED_ORIGINS = [
    "https://aravworks.github.io",   # production frontend (GitHub Pages)
    "http://localhost:3000",         # local frontend dev (python -m http.server)
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"],
)

# ── clients ───────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)

# ═════════════════════════════════════════════════════════
# AUTH HELPER
# ═════════════════════════════════════════════════════════

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        resp = supabase.auth.get_user(token)
        if not resp.user:
            raise HTTPException(401, "Invalid token")
        return resp.user
    except Exception:
        raise HTTPException(401, "Token validation failed")

# ─── helper: fetch profile + diagnosis + past insights ───

def _get_session_context(user_id: str, diagnosis_id: str | None) -> dict:
    """One call to assemble everything Gemini needs. diagnosis_id may be None —
    the assessment is optional, sessions can start without one."""
    profile = supabase.table("profiles").select("name").eq("id", user_id).single().execute()
    user_name = (profile.data or {}).get("name", "there")

    if diagnosis_id:
        diag = supabase.table("diagnoses").select("condition").eq("id", diagnosis_id).single().execute()
        condition = diag.data["condition"] if diag.data else "stress"
    else:
        condition = "stress"   # generic overlay when no assessment has been done yet

    past = (
        supabase.table("sessions")
        .select("insight")
        .eq("user_id", user_id)
        .not_.is_("insight", "null")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    past_insights = [r["insight"] for r in (past.data or []) if r.get("insight")]

    return {"user_name": user_name, "condition": condition, "past_insights": past_insights}


def _parse_ts(ts: str) -> datetime:
    """Parse a Supabase/Postgres timestamptz string into an aware UTC datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _finalize_session(
    session_id: str,
    history: list[dict],
    mood_before: int | None,
    mood_after: int | None,
) -> tuple[str, int | None]:
    """
    Generate the session insight via Gemini and persist it.
    Shared by /session/end and the hard-cap auto-close in /session/message.
    """
    convo_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'MindEase'}: {m['parts'][0]}"
        for m in history
        if m.get("parts")
    )

    insight_prompt = f"""
This was a cognitive therapy session. Extract the single most important insight
the user arrived at. Write it in FIRST PERSON, 1-2 sentences, like a journal entry.
No therapy-speak. Write AS them, not about them.

Good examples:
- "My fear of failure is really about what others think, not the failure itself."
- "I've been catastrophizing — the worst case is manageable, not the end of everything."
- "I can't control the outcome, only what I do today. That's enough."

Conversation:
{convo_text}

Insight (first person, 1-2 sentences only):
"""
    insight_resp = generate_with_fallback(
        lambda name: genai.GenerativeModel(name).generate_content(
            insight_prompt, request_options={"timeout": GEMINI_CALL_TIMEOUT}
        )
    )
    insight = insight_resp.text.strip().strip('"')

    supabase.table("sessions").update({
        "mood_before":    mood_before,
        "mood_after":     mood_after,
        "chat_log_json":  json.dumps(history),
        "insight":        insight,
        "ended_at":       datetime.utcnow().isoformat(),
    }).eq("id", session_id).execute()

    mood_delta = (
        mood_after - mood_before
        if mood_before is not None and mood_after is not None
        else None
    )
    return insight, mood_delta


# ═════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═════════════════════════════════════════════════════════

class DiagnosisRequest(BaseModel):
    condition: str        # anxiety | adhd | stress | sleep
    severity_score: int   # 1–10
    answers_json: dict

class StartSessionRequest(BaseModel):
    diagnosis_id: str | None = None   # assessment is optional
    mode: str = "empathic"   # empathic | socratic | grounding | cbt

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict]
    mode: str = "empathic"

class EndSessionRequest(BaseModel):
    session_id: str
    mood_before: int | None = None
    mood_after: int | None = None
    history: list[dict]

class MoodLogRequest(BaseModel):
    score: int   # 1–5
    note: str = ""

class ExerciseLogRequest(BaseModel):
    type: str            # breathing | thought_journal | grounding | focus_timer
    duration_secs: int = 0

class TherapistSearchRequest(BaseModel):
    city: str = "Kanpur"
    condition: str = ""   # empty → use latest diagnosis

class EmergencyAlertRequest(BaseModel):
    contact_name: str
    contact_phone: str
    contact_email: str


# ═════════════════════════════════════════════════════════
# HEALTH
# ═════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "service": "mindease-api", "version": "1.1.0"}


# ═════════════════════════════════════════════════════════
# PROFILE
# ═════════════════════════════════════════════════════════

@app.get("/api/v1/profile")
def get_profile(user=Depends(get_current_user)):
    profile = supabase.table("profiles").select("name, created_at").eq("id", user.id).single().execute()
    return {
        "name":       (profile.data or {}).get("name", "there"),
        "email":      user.email,
        "created_at": (profile.data or {}).get("created_at"),
    }


# ═════════════════════════════════════════════════════════
# DIAGNOSIS
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/diagnosis")
def save_diagnosis(body: DiagnosisRequest, user=Depends(get_current_user)):
    data = supabase.table("diagnoses").insert({
        "user_id":       user.id,
        "condition":     body.condition,
        "severity_score": body.severity_score,
        "answers_json":  json.dumps(body.answers_json),
        "created_at":    datetime.utcnow().isoformat(),
    }).execute()
    if not data.data:
        raise HTTPException(500, "Failed to save diagnosis")
    return {"diagnosis_id": data.data[0]["id"], "condition": body.condition}


@app.get("/api/v1/diagnosis/latest")
def get_latest_diagnosis(user=Depends(get_current_user)):
    data = (
        supabase.table("diagnoses")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return {"diagnosis": data.data[0] if data.data else None}


# ═════════════════════════════════════════════════════════
# SESSIONS
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/session/start")
def start_session(body: StartSessionRequest, user=Depends(get_current_user)):
    """
    Create session row → build system prompt (persona + condition + mode) →
    get Gemini opening message.
    """
    ctx = _get_session_context(user.id, body.diagnosis_id)

    # Layer 1+2+3: persona + past insights + condition overlay (+ time/day context)
    system_prompt = build_system_prompt(
        ctx["condition"], ctx["user_name"], ctx["past_insights"], get_time_context()
    )
    # Layer 4: therapeutic mode fragment
    system_prompt += "\n" + get_mode_prompt(body.mode)

    # Persist session (store mode so /message can re-inject it)
    now_iso = datetime.utcnow().isoformat()
    session = supabase.table("sessions").insert({
        "user_id":        user.id,
        "diagnosis_id":   body.diagnosis_id,
        "created_at":     now_iso,
        "last_active_at": now_iso,
        # store mode in chat_log_json metadata temporarily
        "chat_log_json": json.dumps({"mode": body.mode, "messages": []}),
    }).execute()
    session_id = session.data[0]["id"]

    opening = generate_with_fallback(
        lambda name: genai.GenerativeModel(name, system_instruction=system_prompt)
            .start_chat(history=[])
            .send_message(
                "Start the session with your opening question. One sentence, warm and direct.",
                request_options={"timeout": GEMINI_CALL_TIMEOUT},
            )
    )

    return {
        "session_id":     session_id,
        "condition":      ctx["condition"],
        "mode":           body.mode,
        "opening_message": opening.text.strip(),
    }


@app.post("/api/v1/session/message")
def send_message(body: ChatMessageRequest, user=Depends(get_current_user)):
    """
    1. Enforce session expiry (30-min inactivity) and hard cap (60-min total)
    2. Run crisis guardrail on user message
    3. If safe → send to Gemini (with full 4-layer prompt + time/day context)
    4. Return reply + crisis_detected flag
    """
    # Fetch session
    session = (
        supabase.table("sessions")
        .select("diagnosis_id, chat_log_json, last_active_at, created_at")
        .eq("id", body.session_id)
        .eq("user_id", user.id)
        .single()
        .execute()
    )
    if not session.data:
        raise HTTPException(404, "Session not found")

    now            = datetime.now(timezone.utc)
    created_dt     = _parse_ts(session.data["created_at"])
    last_active_dt = _parse_ts(session.data.get("last_active_at") or session.data["created_at"])
    session_age    = now - created_dt

    # ── 30-minute inactivity expiry ────────────────────────
    if now - last_active_dt > timedelta(minutes=30):
        raise HTTPException(410, "SESSION_EXPIRED")

    # ── Hard 1-hour session cap — auto-close + save insight ──
    if session_age > timedelta(hours=1):
        insight, mood_delta = _finalize_session(
            body.session_id, body.history, mood_before=None, mood_after=None
        )
        raise HTTPException(410, {
            "error":      "SESSION_TIME_LIMIT",
            "insight":    insight,
            "mood_delta": mood_delta,
        })

    # Any successful interaction from here on counts as activity
    supabase.table("sessions").update({"last_active_at": now.isoformat()}).eq("id", body.session_id).execute()

    # ── Crisis guardrail ──────────────────────────────────
    guard = check_message(body.message)
    if guard["crisis"]:
        return {
            "reply":           (
                "Hey — I need to pause for a second. "
                "What you just said is important and I don't want to gloss over it. "
                "Please reach out to someone who can really support you right now. "
                "Tele-MANAS is free, 24/7, and confidential: 14416."
            ),
            "crisis_detected": True,
            "distress":        False,
        }

    # Soft distress flag → prepend a grounding nudge to the prompt
    distress_note = ""
    if guard.get("distress"):
        distress_note = "\n[Internal note: user seems distressed — be extra gentle this message.]\n"

    # ── Build Gemini context ──────────────────────────────
    diag_id = session.data["diagnosis_id"]
    ctx     = _get_session_context(user.id, diag_id)

    # Recover stored mode from session metadata
    stored  = json.loads(session.data.get("chat_log_json") or "{}")
    mode    = body.mode or stored.get("mode", "empathic")

    system_prompt = (
        build_system_prompt(ctx["condition"], ctx["user_name"], ctx["past_insights"], get_time_context())
        + "\n" + get_mode_prompt(mode)
        + distress_note
    )

    response = generate_with_fallback(
        lambda name: genai.GenerativeModel(name, system_instruction=system_prompt)
            .start_chat(history=body.history)
            .send_message(body.message, request_options={"timeout": GEMINI_CALL_TIMEOUT})
    )
    reply = response.text.strip()

    # ── 50-minute soft warning (session still open, cap is close) ──
    if timedelta(minutes=50) < session_age <= timedelta(hours=1):
        reply += (
            "\n\n[We've been talking for 50 minutes — this session closes at 60. "
            "Want to start wrapping up and save today's insight?]"
        )

    return {
        "reply":           reply,
        "crisis_detected": False,
        "distress":        guard.get("distress", False),
    }


@app.post("/api/v1/session/end")
def end_session(body: EndSessionRequest, user=Depends(get_current_user)):
    """
    Generate session insight via a dedicated Gemini call → save everything.
    """
    session = (
        supabase.table("sessions")
        .select("diagnosis_id")
        .eq("id", body.session_id)
        .eq("user_id", user.id)
        .single()
        .execute()
    )
    if not session.data:
        raise HTTPException(404, "Session not found")

    insight, mood_delta = _finalize_session(
        body.session_id, body.history, body.mood_before, body.mood_after
    )

    return {
        "session_id": body.session_id,
        "insight":    insight,
        "mood_delta": mood_delta,
    }


@app.get("/api/v1/session/history")
def get_session_history(user=Depends(get_current_user), limit: int = 20):
    data = (
        supabase.table("sessions")
        .select("id, created_at, ended_at, insight, mood_before, mood_after, diagnoses(condition)")
        .eq("user_id", user.id)
        .not_.is_("ended_at", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"sessions": data.data or []}


# ═════════════════════════════════════════════════════════
# MOOD LOGS
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/mood")
def log_mood(body: MoodLogRequest, user=Depends(get_current_user)):
    data = supabase.table("mood_logs").insert({
        "user_id":   user.id,
        "score":     body.score,
        "note":      body.note,
        "logged_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"logged": True, "mood_id": data.data[0]["id"]}


@app.get("/api/v1/mood/history")
def get_mood_history(user=Depends(get_current_user), days: int = 30):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    data = (
        supabase.table("mood_logs")
        .select("score, note, logged_at")
        .eq("user_id", user.id)
        .gte("logged_at", since)
        .order("logged_at", desc=False)
        .execute()
    )
    return {"mood_history": data.data or []}


# ═════════════════════════════════════════════════════════
# EXERCISES
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/exercise")
def log_exercise(body: ExerciseLogRequest, user=Depends(get_current_user)):
    """Log a completed breathing / grounding / thought-journal / focus-timer exercise."""
    data = supabase.table("exercises").insert({
        "user_id":       user.id,
        "type":          body.type,
        "duration_secs": body.duration_secs,
        "completed_at":  datetime.utcnow().isoformat(),
    }).execute()
    return {"logged": True, "exercise_id": data.data[0]["id"]}


@app.get("/api/v1/exercise/history")
def get_exercise_history(user=Depends(get_current_user), days: int = 30):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    data = (
        supabase.table("exercises")
        .select("type, duration_secs, completed_at")
        .eq("user_id", user.id)
        .gte("completed_at", since)
        .order("completed_at", desc=True)
        .execute()
    )
    return {"exercise_history": data.data or []}


# ═════════════════════════════════════════════════════════
# VOICE / STT + SER
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """
    Accept an audio file → Whisper transcription → Gemini emotion analysis.
    Returns transcript + SER scores + a context string ready to prepend to a session.
    """
    if audio.content_type not in ("audio/webm", "audio/wav", "audio/mp4", "audio/mpeg", "audio/ogg"):
        raise HTTPException(400, f"Unsupported audio type: {audio.content_type}")

    audio_bytes = await audio.read()
    if len(audio_bytes) > 25 * 1024 * 1024:   # 25 MB Whisper limit
        raise HTTPException(413, "Audio file too large (max 25 MB)")

    try:
        result = process_voice_input(audio_bytes, filename=audio.filename or "audio.webm")
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {e}")

    # Log as an exercise entry
    supabase.table("exercises").insert({
        "user_id":      user.id,
        "type":         "voice_journal",
        "duration_secs": int(result.get("duration_secs", 0)),
        "completed_at": datetime.utcnow().isoformat(),
    }).execute()

    return result


# ═════════════════════════════════════════════════════════
# THERAPIST FINDER
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/therapist/search")
def search_therapists(body: TherapistSearchRequest, user=Depends(get_current_user)):
    """
    Scrape Practo for therapists matching the user's diagnosis + city.
    Falls back to curated static list if scraping is blocked.
    """
    condition = body.condition
    if not condition:
        # Pull from latest diagnosis
        diag = (
            supabase.table("diagnoses")
            .select("condition")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        condition = diag.data[0]["condition"] if diag.data else "stress"

    therapists = find_therapists(city=body.city, condition=condition)
    return {"therapists": therapists, "condition": condition, "city": body.city}


# ═════════════════════════════════════════════════════════
# PDF REPORT
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/report/generate")
def generate_report(user=Depends(get_current_user)):
    """
    Pull all user data → ask Gemini to extract top triggers →
    build ReportLab PDF → return as binary response.
    """
    # Profile
    profile = supabase.table("profiles").select("name").eq("id", user.id).single().execute()
    user_name = (profile.data or {}).get("name", "User")

    # Latest diagnosis
    diag = (
        supabase.table("diagnoses")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not diag.data:
        raise HTTPException(400, "No diagnosis found — complete the assessment first")
    d = diag.data[0]
    condition      = d["condition"]
    severity_score = d["severity_score"]
    answers_json   = json.loads(d.get("answers_json") or "{}")

    # Mood history (30 days)
    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    moods = (
        supabase.table("mood_logs")
        .select("score, logged_at")
        .eq("user_id", user.id)
        .gte("logged_at", since)
        .order("logged_at")
        .execute()
    )

    # Sessions with insights
    sessions = (
        supabase.table("sessions")
        .select("insight, mood_before, mood_after, created_at")
        .eq("user_id", user.id)
        .not_.is_("insight", "null")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    session_rows = sessions.data or []

    # Extract top triggers via Gemini
    insights_text = "\n".join(
        f"- {s['insight']}" for s in session_rows if s.get("insight")
    ) or "No session insights yet."

    trigger_prompt = f"""
Based on these session insights from a person with {condition}, list the top 3-5
recurring themes or triggers as short phrases (5-8 words each).
No bullet symbols, no numbers — just one phrase per line.

Insights:
{insights_text}

Top themes/triggers:
"""
    trigger_resp = generate_with_fallback(
        lambda name: genai.GenerativeModel(name).generate_content(
            trigger_prompt, request_options={"timeout": GEMINI_CALL_TIMEOUT}
        )
    )
    top_triggers = [
        line.strip() for line in trigger_resp.text.strip().split("\n")
        if line.strip()
    ][:5]

    # Generate PDF
    pdf_bytes = generate_pdf(
        user_name      = user_name,
        condition      = condition,
        severity_score = severity_score,
        assessment_answers = answers_json,
        mood_history   = moods.data or [],
        sessions       = session_rows,
        top_triggers   = top_triggers,
    )

    return Response(
        content     = pdf_bytes,
        media_type  = "application/pdf",
        headers     = {"Content-Disposition": f'attachment; filename="MindEase_Report_{user_name}.pdf"'},
    )


# ═════════════════════════════════════════════════════════
# CRISIS ALERT
# ═════════════════════════════════════════════════════════

@app.post("/api/v1/crisis/alert")
def crisis_alert(body: EmergencyAlertRequest, user=Depends(get_current_user)):
    """
    Send SMS + email to user's emergency contact via Twilio + SendGrid.
    Only called when user explicitly taps "Alert my emergency contact."
    """
    profile = supabase.table("profiles").select("name").eq("id", user.id).single().execute()
    user_name = (profile.data or {}).get("name", "A MindEase user")

    result = send_emergency_alert(
        contact_name  = body.contact_name,
        contact_phone = body.contact_phone,
        contact_email = body.contact_email,
        user_name     = user_name,
    )
    return {"alert_sent": result}