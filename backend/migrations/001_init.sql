-- 001_init.sql — extensions, enums, shared helpers
-- Tafahhum · Sudais Khalid

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- trigram matching for Arabic fuzzy lookup
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector
-- btree_gist lets a plain integer column sit inside a GiST index alongside a
-- range type, which is what the (surah_number, ayah range) overlap index needs.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ---------------------------------------------------------------------------
-- Corpus lifecycle (SOURCE_POLICY §3)
-- ---------------------------------------------------------------------------
CREATE TYPE corpus_status AS ENUM (
    'DISCOVERED',
    'ACQUIRED',
    'SCANNED',
    'OCR_COMPLETE',
    'NORMALIZED',
    'AYAH_ALIGNED',
    'METADATA_COMPLETE',
    'HUMAN_REVIEW',
    'VERIFIED',
    'INDEXED',
    'PUBLISHED'
);

-- Verification state of an individual row. FIXTURE is a hard-excluded test state:
-- it exists so that test data can never leak into a user-facing result set.
CREATE TYPE verification_status AS ENUM (
    'FIXTURE',
    'UNVERIFIED',
    'MACHINE_PROPOSED',
    'IN_REVIEW',
    'DISPUTED',
    'VERIFIED'
);

-- The eight evidence kinds that must never be silently merged (SOURCE_POLICY §8)
CREATE TYPE evidence_type AS ENUM (
    'QURANIC_TEXT',
    'HADITH',
    'COMPANION_REPORT',
    'TABII_REPORT',
    'MUFASSIR_INTERPRETATION',
    'LATER_SCHOLARLY_INTERPRETATION',
    'MODERN_ACADEMIC_ANALYSIS',
    'TAFAHHUM_SYNTHESIS'
);

-- Historical periodisation. Boundaries are conventional, not absolute; the
-- authoritative field is always the Hijri death year on the Mufassir record.
CREATE TYPE historical_period AS ENUM (
    'FORMATIVE',    -- companions and successors
    'EARLY',        -- to ~ 4th century AH
    'CLASSICAL',    -- ~ 4th – 7th century AH
    'MEDIEVAL',     -- ~ 7th – 10th century AH
    'LATER',        -- ~ 10th – 13th century AH
    'MODERN',       -- ~ 13th century AH onward
    'UNKNOWN'
);

CREATE TYPE language_code AS ENUM ('ar', 'en', 'ur', 'fa', 'tr', 'ms', 'other');

CREATE TYPE coverage_kind AS ENUM ('COMPLETE', 'PARTIAL', 'FRAGMENTARY', 'LOST', 'UNKNOWN');

CREATE TYPE copyright_status AS ENUM (
    'PUBLIC_DOMAIN',
    'PUBLIC_DOMAIN_TEXT_EDITION_RESTRICTED',  -- old text, modern critical apparatus
    'LICENSED',
    'RESTRICTED',
    'UNKNOWN'
);

-- ---------------------------------------------------------------------------
-- Shared helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Arabic full-text configuration. PostgreSQL ships an 'arabic' snowball stemmer;
-- we index the *normalized* column, so the stemmer sees consistent orthography.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'tafahhum_ar') THEN
        CREATE TEXT SEARCH CONFIGURATION tafahhum_ar (COPY = arabic);
    END IF;
END
$$;

-- Migration bookkeeping
CREATE TABLE IF NOT EXISTS schema_migration (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now(),
    checksum    text NOT NULL
);
