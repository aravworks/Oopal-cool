-- ═══════════════════════════════════════════════════════
-- MindEase — RLS re-enable (URGENT)
-- Run this immediately in Supabase SQL Editor.
-- Right now every table is readable/writable by the public anon key
-- with NO authentication — this closes that hole.
-- Safe to re-run.
-- ═══════════════════════════════════════════════════════

ALTER TABLE profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnoses ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE mood_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;

-- ── Verification: all 5 should show rowsecurity = true ────
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname IN ('profiles', 'diagnoses', 'sessions', 'mood_logs', 'exercises')
ORDER BY relname;

-- ── Verification: confirm the ownership policies still exist ──
-- (disabling RLS does NOT drop policies, so these should already be there
--  from the original schema.sql — this just confirms nothing was lost)
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('profiles', 'diagnoses', 'sessions', 'mood_logs', 'exercises')
ORDER BY tablename, policyname;
