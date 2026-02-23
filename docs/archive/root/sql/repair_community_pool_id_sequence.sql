-- Fix PostgreSQL sequence drift for community_pool.id (safe / non-destructive)
--
-- What it does:
-- - Reads MAX(id) from public.community_pool
-- - Reads the sequence's current "next" value
-- - Sets the sequence so the NEXT id will be > MAX(id)
-- - Never decreases the sequence (avoids ID reuse)
--
-- Run:
--   psql "$DATABASE_URL" -f repair_community_pool_id_sequence.sql

DO $$
DECLARE
    seq_reg regclass;
    max_id bigint;
    last_val bigint;
    called boolean;
    current_next bigint;
    target_next bigint;
BEGIN
    SELECT pg_get_serial_sequence('public.community_pool', 'id')::regclass
    INTO seq_reg;

    IF seq_reg IS NULL THEN
        RAISE NOTICE 'No serial/identity sequence found for public.community_pool.id';
        RETURN;
    END IF;

    SELECT COALESCE(MAX(id), 0) INTO max_id FROM public.community_pool;
    EXECUTE format('SELECT last_value, is_called FROM %s', seq_reg) INTO last_val, called;

    current_next := CASE WHEN called THEN last_val + 1 ELSE last_val END;
    target_next := GREATEST(max_id + 1, current_next);

    PERFORM setval(seq_reg, target_next, false);
END $$;

