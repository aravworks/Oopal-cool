"""
MindEase — Database Seeder
Creates one demo user with realistic session history, mood logs, and insights.
Run this after setting up the schema: python seed_db.py

Usage:
  cd scripts
  python seed_db.py
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))

from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)

DEMO_EMAIL    = "demo@mindease.app"
DEMO_PASSWORD = "MindEase@Demo2026"
DEMO_NAME     = "Arjun"

SAMPLE_INSIGHTS = [
    "My fear of failure is really about what others will think of me — not the failure itself.",
    "I can't control the outcome, only what I do today. That's actually enough.",
    "The spiral starts when I stop moving. Even a short walk interrupts it.",
    "I've been catastrophizing — the actual worst case is manageable, not the end of everything.",
    "I keep saying 'I should be further along.' Says who? That rule isn't even mine.",
    "When I'm anxious, I'm living in a future that hasn't happened yet.",
]

SAMPLE_ASSESSMENT = {
    "When do you feel lowest during the day?":
        "Evening — thoughts spiral at night",
    "What kind of thoughts repeat most often?":
        "Worry about failing and what people think of me",
    "What have you tried before that helped, even a little?":
        "Going for walks, talking to a close friend",
}


def seed():
    print("🌱 Seeding MindEase demo data...\n")

    # 1. Create auth user
    try:
        auth_resp = supabase.auth.admin.create_user({
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "email_confirm": True,
            "user_metadata": {"name": DEMO_NAME},
        })
        user_id = auth_resp.user.id
        print(f"✅ Created user: {DEMO_EMAIL} (id: {user_id})")
    except Exception as e:
        if "already been registered" in str(e):
            users = supabase.auth.admin.list_users()
            user_id = next(u.id for u in users if u.email == DEMO_EMAIL)
            print(f"ℹ️  User already exists (id: {user_id})")
        else:
            print(f"❌ User creation failed: {e}")
            sys.exit(1)

    # 2. Update profile name
    supabase.table("profiles").upsert({"id": user_id, "name": DEMO_NAME}).execute()
    print("✅ Profile set")

    # 3. Create diagnosis
    diag = supabase.table("diagnoses").insert({
        "user_id":       user_id,
        "condition":     "anxiety",
        "severity_score": 6,
        "answers_json":  json.dumps(SAMPLE_ASSESSMENT),
        "created_at":    (datetime.utcnow() - timedelta(days=14)).isoformat(),
    }).execute()
    diag_id = diag.data[0]["id"]
    print(f"✅ Diagnosis created (id: {diag_id})")

    # 4. Create 6 sessions with insights
    for i, insight in enumerate(SAMPLE_INSIGHTS):
        days_ago    = 14 - (i * 2)
        mood_before = random.randint(1, 3)
        mood_after  = min(5, mood_before + random.randint(1, 2))
        created_at  = datetime.utcnow() - timedelta(days=days_ago)
        supabase.table("sessions").insert({
            "user_id":       user_id,
            "diagnosis_id":  diag_id,
            "insight":       insight,
            "mood_before":   mood_before,
            "mood_after":    mood_after,
            "chat_log_json": json.dumps([]),   # empty for demo
            "created_at":    created_at.isoformat(),
            "ended_at":      (created_at + timedelta(minutes=28)).isoformat(),
        }).execute()
    print(f"✅ Created {len(SAMPLE_INSIGHTS)} sessions with insights")

    # 5. Create 14 days of mood logs
    for day in range(14, 0, -1):
        score = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 30, 30, 20])[0]
        supabase.table("mood_logs").insert({
            "user_id":   user_id,
            "score":     score,
            "note":      "",
            "logged_at": (datetime.utcnow() - timedelta(days=day)).isoformat(),
        }).execute()
    print("✅ Created 14 days of mood logs")

    # 6. Create exercise logs
    for day in [10, 8, 6, 4, 2, 1]:
        supabase.table("exercises").insert({
            "user_id":      user_id,
            "type":         random.choice(["breathing", "grounding", "thought_journal"]),
            "duration_secs": random.randint(180, 420),
            "completed_at": (datetime.utcnow() - timedelta(days=day)).isoformat(),
        }).execute()
    print("✅ Created exercise logs\n")

    print("🎉 Seeding complete!")
    print(f"   Email:    {DEMO_EMAIL}")
    print(f"   Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
