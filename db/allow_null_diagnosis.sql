-- ═══════════════════════════════════════════════════════
-- MindEase — Make diagnosis optional for sessions
-- Run once in Supabase SQL Editor. Safe to re-run.
-- ═══════════════════════════════════════════════════════

ALTER TABLE sessions ALTER COLUMN diagnosis_id DROP NOT NULL;

-- ── Verification ────────────────────────────────────────
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'sessions' AND column_name = 'diagnosis_id';
