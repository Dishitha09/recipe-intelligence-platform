DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_available_extensions
        WHERE name = 'pg_trgm'
    ) THEN
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    ELSE
        RAISE NOTICE 'pg_trgm is not installed on this PostgreSQL server; fuzzy name indexes will be skipped.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_available_extensions
        WHERE name = 'vector'
    ) THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    ELSE
        RAISE NOTICE 'pgvector is not installed on this PostgreSQL server; vector tables will be skipped.';
    END IF;
END $$;
