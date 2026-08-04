-- ═══════════════════════════════════════════════════════
-- MindEase — Signup trigger fix
-- Run this once in Supabase SQL Editor (dashboard.supabase.com → SQL Editor)
-- Safe to re-run — CREATE OR REPLACE is idempotent.
-- ═══════════════════════════════════════════════════════

-- Fixes "Database error saving new user" on signup.
-- Root cause: a SECURITY DEFINER trigger function without an explicit
-- search_path can fail to resolve `profiles` when fired from the
-- auth schema's insert context.
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.profiles (id, name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'name', 'User'));
    RETURN NEW;
END;
$$;

-- ── Verification: confirm the fix applied ─────────────────
-- Should show search_path=public in the function's config
SELECT proname, proconfig
FROM pg_proc
WHERE proname = 'handle_new_user';

-- ── Verification: confirm all 5 tables exist with RLS on ──
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname IN ('profiles', 'diagnoses', 'sessions', 'mood_logs', 'exercises')
ORDER BY relname;

-- ── After testing signup once, verify data landed correctly ──
-- (run as service role / in SQL editor, which bypasses RLS)
SELECT id, name, created_at FROM profiles ORDER BY created_at DESC LIMIT 5;
SELECT id, user_id, condition, severity_score, created_at FROM diagnoses ORDER BY created_at DESC LIMIT 5;
SELECT id, user_id, insight, mood_before, mood_after, ended_at FROM sessions ORDER BY created_at DESC LIMIT 5;
SELECT id, user_id, score, note, logged_at FROM mood_logs ORDER BY logged_at DESC LIMIT 10;
SELECT id, user_id, type, duration_secs, completed_at FROM exercises ORDER BY completed_at DESC LIMIT 10;

-- ── One-time cleanup: remove any bogus "breathing exercise" mood_logs ──
-- rows created by the old frontend bug before this fix. Review before running —
-- this deletes any mood_logs row whose note literally says "breathing exercise".
-- DELETE FROM mood_logs WHERE note = 'breathing exercise';
