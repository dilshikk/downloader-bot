-- Migration: fix favorites table
-- Run this script ONCE on the server if the favorites table was created
-- without the tg_id column (old schema had a different structure).
--
-- Usage:
--   psql -U <user> -d <database> -f migrations/001_fix_favorites_table.sql

DO $$
BEGIN
    -- Check if tg_id column is missing and recreate the table if needed
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'favorites' AND column_name = 'tg_id'
    ) THEN
        -- Drop old table (it had wrong schema)
        DROP TABLE IF EXISTS favorites;

        -- Create with correct schema
        CREATE TABLE favorites (
            id          SERIAL PRIMARY KEY,
            tg_id       BIGINT NOT NULL,
            file_id     TEXT NOT NULL,
            title       TEXT NOT NULL,
            created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(tg_id, file_id)
        );

        RAISE NOTICE 'favorites table recreated with correct schema';
    ELSE
        RAISE NOTICE 'favorites table already has tg_id column, skipping';
    END IF;
END
$$;
