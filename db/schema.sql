-- ═══════════════════════════════════════════════════════
-- MindEase — Supabase Schema + RLS
-- Run this in Supabase SQL Editor (dashboard.supabase.com)
-- ═══════════════════════════════════════════════════════


-- ── 1. PROFILES ──────────────────────────────────────────
-- Extends Supabase auth.users with display name

CREATE TABLE profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.profiles (id, name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'name', 'User'));
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();


-- ── 2. DIAGNOSES ─────────────────────────────────────────
-- Assessment results — the user's "diagnosis"

CREATE TABLE diagnoses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    condition       TEXT NOT NULL CHECK (condition IN ('anxiety', 'adhd', 'stress', 'sleep')),
    severity_score  INT NOT NULL CHECK (severity_score BETWEEN 1 AND 10),
    answers_json    JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE diagnoses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own diagnoses"
    ON diagnoses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users insert own diagnoses"
    ON diagnoses FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- ── 3. SESSIONS ───────────────────────────────────────────
-- Each therapy chat session. insight = the "cure" saved to chart.

CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    diagnosis_id    UUID REFERENCES diagnoses(id),   -- nullable: assessment is optional
    chat_log_json   JSONB,           -- full conversation history
    insight         TEXT,            -- AI-generated session insight (the "cure")
    mood_before     INT CHECK (mood_before BETWEEN 1 AND 5),
    mood_after      INT CHECK (mood_after BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ DEFAULT NOW(),  -- bumped on every message; drives the 30-min inactivity expiry
    ended_at        TIMESTAMPTZ      -- NULL = session still active
);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own sessions"
    ON sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users insert own sessions"
    ON sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own sessions"
    ON sessions FOR UPDATE
    USING (auth.uid() = user_id);


-- ── 4. MOOD LOGS ─────────────────────────────────────────
-- Daily mood check-ins. Powers the trend chart.

CREATE TABLE mood_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    score       INT NOT NULL CHECK (score BETWEEN 1 AND 5),
    note        TEXT DEFAULT '',
    logged_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE mood_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own mood logs"
    ON mood_logs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users insert own mood logs"
    ON mood_logs FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- ── 5. EXERCISES ─────────────────────────────────────────
-- Completed CBT/grounding exercises

CREATE TABLE exercises (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,   -- breathing | thought_journal | grounding | focus_timer
    duration_secs   INT,
    completed_at    TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own exercises"
    ON exercises FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users insert own exercises"
    ON exercises FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- ── INDEXES ───────────────────────────────────────────────
-- Speed up the queries that run most often

CREATE INDEX idx_sessions_user_created ON sessions(user_id, created_at DESC);
CREATE INDEX idx_mood_logs_user_logged  ON mood_logs(user_id, logged_at DESC);
CREATE INDEX idx_diagnoses_user_created ON diagnoses(user_id, created_at DESC);
