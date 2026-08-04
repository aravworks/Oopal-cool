"""
MindEase — End-to-End Session Smoke Test
Tests the full session flow against a running FastAPI backend.

Usage:
  cd scripts
  python test_session.py

Requires:
  - Backend running at http://localhost:8000
  - Demo user seeded (run seed_db.py first)
  - pip install requests
"""

import sys
import json
import requests

BASE_URL      = "http://localhost:8000"
DEMO_EMAIL    = "demo@mindease.app"
DEMO_PASSWORD = "MindEase@Demo2026"

SUPABASE_URL  = None  # loaded from .env
SUPABASE_KEY  = None

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_ANON_KEY"]


def log(label: str, data=None, ok=True):
    icon = "✅" if ok else "❌"
    print(f"{icon} {label}")
    if data:
        print(f"   {json.dumps(data, indent=2)[:200]}")


def get_token() -> str:
    """Sign in via Supabase REST API and get JWT."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log("Auth: got JWT token")
    return token


def run_tests():
    print("\n🧪 MindEase End-to-End Session Test\n")

    # ── 1. Health check ───────────────────────────────────
    try:
        r = requests.get(f"{BASE_URL}/health")
        r.raise_for_status()
        log("Health check", r.json())
    except Exception as e:
        log(f"Health check FAILED — is the server running? {e}", ok=False)
        sys.exit(1)

    # ── 2. Auth ───────────────────────────────────────────
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        log(f"Auth failed: {e}", ok=False)
        sys.exit(1)

    # ── 3. Get latest diagnosis ───────────────────────────
    r = requests.get(f"{BASE_URL}/api/v1/diagnosis/latest", headers=headers)
    r.raise_for_status()
    diag = r.json()["diagnosis"]
    log("Got latest diagnosis", {"condition": diag["condition"], "severity": diag["severity_score"]})
    diag_id = diag["id"]

    # ── 4. Start session ──────────────────────────────────
    r = requests.post(
        f"{BASE_URL}/api/v1/session/start",
        headers=headers,
        json={"diagnosis_id": diag_id},
    )
    r.raise_for_status()
    session_data = r.json()
    log("Session started", {"session_id": session_data["session_id"][:8] + "...", "opening": session_data["opening_message"][:80]})
    session_id = session_data["session_id"]

    # ── 5. Exchange messages ──────────────────────────────
    history = [{"role": "model", "parts": [session_data["opening_message"]]}]
    test_messages = [
        "I've been really anxious about my exams lately. Can't stop thinking about failing.",
        "Yeah I know logically it's not the end of the world but it feels like it is.",
        "I think I'm scared of what people will think of me if I fail.",
    ]

    for msg in test_messages:
        r = requests.post(
            f"{BASE_URL}/api/v1/session/message",
            headers=headers,
            json={"session_id": session_id, "message": msg, "history": history},
        )
        r.raise_for_status()
        reply = r.json()["reply"]
        history.append({"role": "user",  "parts": [msg]})
        history.append({"role": "model", "parts": [reply]})
        log(f"Message exchange", {"user": msg[:50], "ai": reply[:80]})

    # ── 6. End session ────────────────────────────────────
    r = requests.post(
        f"{BASE_URL}/api/v1/session/end",
        headers=headers,
        json={
            "session_id": session_id,
            "mood_before": 2,
            "mood_after":  3,
            "history":     history,
        },
    )
    r.raise_for_status()
    end_data = r.json()
    log("Session ended", {"insight": end_data["insight"], "mood_delta": end_data["mood_delta"]})

    # ── 7. Mood log ───────────────────────────────────────
    r = requests.post(
        f"{BASE_URL}/api/v1/mood",
        headers=headers,
        json={"score": 3, "note": "Test mood log"},
    )
    r.raise_for_status()
    log("Mood logged", r.json())

    # ── 8. Session history ────────────────────────────────
    r = requests.get(f"{BASE_URL}/api/v1/session/history", headers=headers)
    r.raise_for_status()
    sessions = r.json()["sessions"]
    log(f"Session history: {len(sessions)} sessions found")

    print("\n🎉 All tests passed!\n")


if __name__ == "__main__":
    run_tests()
