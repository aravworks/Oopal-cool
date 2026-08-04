"""
MindEase — Crisis Guardrail Layer
Runs on every user message before it reaches the main Gemini session.
Two-layer detection: fast keyword scan → Gemini intent classifier.
"""

import os
import google.generativeai as genai

# ── Keyword list ──────────────────────────────────────────────────────────────
# English + common Hinglish crisis phrases
CRISIS_KEYWORDS = [
    # English
    "kill myself", "end my life", "want to die", "don't want to be here",
    "wish i was dead", "better off dead", "no reason to live",
    "can't go on", "not worth living", "ending it all",
    "self harm", "self-harm", "hurt myself", "cutting myself",
    "suicide", "suicidal", "overdose", "take my life",
    "disappear forever", "everyone would be better without me",
    "no point anymore", "nothing left",
    # Hinglish / Hindi transliterated
    "marna chahta", "marna chahti", "jina nahi chahta", "jina nahi chahti",
    "khatam karna chahta", "khatam kar lu", "khud ko hurt",
    "ji nahi chahta", "sab chhod du", "mar jau",
    "zindagi nahi chahiye", "maut chahiye",
]

# Lower-severity phrases that warrant a soft check-in, not full crisis mode
SOFT_FLAGS = [
    "i give up", "what's the point", "so tired of everything",
    "can't take it anymore", "nobody cares", "completely alone",
    "thak gaya", "thak gayi", "koi nahi hai", "akela hoon", "akeli hoon",
]


def scan_keywords(text: str) -> dict:
    """Fast O(n) keyword scan. Returns immediately on first match."""
    text_lower = text.lower()
    for kw in CRISIS_KEYWORDS:
        if kw in text_lower:
            return {"crisis": True, "severity": "high", "method": "keyword", "matched": kw}
    for kw in SOFT_FLAGS:
        if kw in text_lower:
            return {"crisis": False, "severity": "soft", "method": "keyword", "matched": kw}
    return {"crisis": False, "severity": "none", "method": "keyword"}


def classify_intent(text: str) -> dict:
    """
    Gemini intent classification — runs only if keyword scan is negative
    but the message is longer and emotionally charged.
    Returns {"crisis": bool, "confidence": float}
    """
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = f"""You are a safety classifier for a mental health app.
Analyse the message below and answer ONLY with one of these three words:
  CRISIS     — message contains suicidal ideation, self-harm intent, or imminent danger
  DISTRESS   — message shows significant emotional pain but no immediate safety risk
  SAFE       — message is general emotional expression, venting, or neutral

Message: "{text}"

Your answer (one word only):"""
        resp = model.generate_content(prompt)
        label = resp.text.strip().upper().split()[0]
        return {
            "crisis":     label == "CRISIS",
            "distress":   label == "DISTRESS",
            "confidence": 0.9,
            "method":     "llm",
            "label":      label,
        }
    except Exception:
        # If classification fails, default to safe — don't block the session
        return {"crisis": False, "distress": False, "confidence": 0.0, "method": "llm_error"}


def check_message(text: str) -> dict:
    """
    Main entry point. Called by the /session/message route on every user message.

    Returns:
      {
        "crisis":   bool,   — trigger full crisis UI
        "distress": bool,   — trigger soft check-in prompt
        "severity": str,    — "high" | "soft" | "none"
        "method":   str,    — "keyword" | "llm" | "llm_error"
      }
    """
    # Layer 1: keyword scan (fast, no API call)
    kw_result = scan_keywords(text)

    if kw_result["crisis"]:
        return {**kw_result, "distress": False}

    if kw_result["severity"] == "soft":
        return {**kw_result, "crisis": False, "distress": True}

    # Layer 2: LLM classification — only for longer messages (>20 words)
    # to avoid unnecessary API calls on short replies
    if len(text.split()) > 20:
        llm_result = classify_intent(text)
        return {
            "crisis":   llm_result["crisis"],
            "distress": llm_result.get("distress", False),
            "severity": "high" if llm_result["crisis"] else "soft" if llm_result.get("distress") else "none",
            "method":   llm_result["method"],
        }

    return {"crisis": False, "distress": False, "severity": "none", "method": "keyword"}


# ── Emergency alert ───────────────────────────────────────────────────────────

def send_emergency_alert(
    contact_name: str,
    contact_phone: str,
    contact_email: str,
    user_name: str,
) -> dict:
    """
    Sends SMS + email to the user's saved emergency contact.
    Called only when user explicitly taps "Alert my emergency contact."
    """
    results = {}

    # SMS via Twilio
    try:
        from twilio.rest import Client
        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        msg = client.messages.create(
            body=(
                f"Hi {contact_name}, this is an automated message from MindEase. "
                f"{user_name} has indicated they may need support right now. "
                f"Please reach out to them when you can. "
                f"If you believe they're in immediate danger, call 112."
            ),
            from_=os.environ["TWILIO_FROM_NUMBER"],
            to=contact_phone,
        )
        results["sms"] = {"sent": True, "sid": msg.sid}
    except Exception as e:
        results["sms"] = {"sent": False, "error": str(e)}

    # Email via SendGrid
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])
        mail = Mail(
            from_email="support@mindease.app",
            to_emails=contact_email,
            subject=f"MindEase: {user_name} may need your support",
            html_content=(
                f"<p>Hi {contact_name},</p>"
                f"<p>{user_name} has used MindEase's emergency contact feature, "
                f"which means they may be going through a difficult time right now.</p>"
                f"<p>Please reach out to them. If you believe they're in immediate danger, "
                f"call emergency services (112).</p>"
                f"<p>National helpline: <strong>Tele-MANAS 14416</strong></p>"
                f"<p>— MindEase Safety Team</p>"
            ),
        )
        sg.send(mail)
        results["email"] = {"sent": True}
    except Exception as e:
        results["email"] = {"sent": False, "error": str(e)}

    return results
