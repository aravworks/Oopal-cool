-- ═══════════════════════════════════════════════════════
-- MindEase — Session timing migration
-- Run this once in Supabase SQL Editor (dashboard.supabase.com → SQL Editor)
-- Safe to re-run — IF NOT EXISTS guards make it idempotent.
-- ═══════════════════════════════════════════════════════

-- Adds last_active_at, used to enforce:
--   - 30-minute inactivity expiry
--   - 60-minute hard session cap (measured from created_at, no new column needed)
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill: for any existing open sessions, seed last_active_at from created_at
-- so they don't immediately look "expired" the first time someone messages them.
UPDATE sessions
SET last_active_at = created_at
WHERE last_active_at IS NULL;

-- ── Verification ────────────────────────────────────────
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'sessions' AND column_name = 'last_active_at';
