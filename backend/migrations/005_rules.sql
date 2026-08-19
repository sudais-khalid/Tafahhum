-- 005_rules.sql — the scholarly rule engine and its provenance
--
-- Every retrieval decision must be explainable, and every explanation must
-- terminate in a citation. The constraints below make an unsourced scholarly
-- rule unrepresentable rather than merely discouraged.

CREATE TYPE query_type AS ENUM (
    'AYAH_TAFSIR',
    'WORD_MEANING',
    'LINGUISTIC',
    'ASBAB_AL_NUZUL',
    'FIQH',
    'AQEEDAH',
    'HADITH',
    'QIRAAT',
    'HISTORICAL',
    'COMPARATIVE',
    'MUFASSIR_SPECIFIC',
    'TAFSIR_SPECIFIC',
    'THEMATIC',
    'SCHOLARLY_DISAGREEMENT',
    'MUFASSIR_BIOGRAPHY',
    'SOURCE_SEARCH',
    'UNKNOWN'
);

-- Rule tiers, evaluated in this order. A lower tier can never override a
-- higher one (§22): generation-layer preferences cannot loosen a scholarly
-- constraint, and a scholarly constraint cannot loosen source provenance.
CREATE TYPE rule_tier AS ENUM (
    'SYSTEM_INTEGRITY',      -- 1
    'SOURCE_PROVENANCE',     -- 2
    'SCHOLARLY_METHOD',      -- 3  <- only tier permitted to make scholarly claims
    'QUERY_STRATEGY',        -- 4
    'EVIDENCE_QUALITY',      -- 5
    'RESPONSE_STRUCTURE',    -- 6
    'LANGUAGE_GENERATION'    -- 7
);

-- The sentinel used by rules that make no scholarly claim at all.
-- Structural rules are labelled with this and are never attributed to a book.
CREATE TABLE scholarly_rule (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key            text NOT NULL UNIQUE,
    name                text NOT NULL,
    description         text NOT NULL,
    tier                rule_tier NOT NULL,
    priority            int NOT NULL DEFAULT 100,   -- lower runs first within a tier

    -- Provenance. 'TAFAHHUM_BASELINE' means: structural, makes no scholarly claim.
    source_book         text NOT NULL,
    biblio_source_id    uuid REFERENCES biblio_source(id) ON DELETE RESTRICT,
    source_reference    text,           -- volume/page, required for scholarly rules
    source_quote_ar     text,

    -- Applicability
    applies_to_query_types query_type[] NOT NULL DEFAULT '{}',
    condition           jsonb NOT NULL DEFAULT '{}'::jsonb,

    -- Effects on retrieval
    required_source_slugs  text[] NOT NULL DEFAULT '{}',
    preferred_source_slugs text[] NOT NULL DEFAULT '{}',
    excluded_source_slugs  text[] NOT NULL DEFAULT '{}',
    effects             jsonb NOT NULL DEFAULT '{}'::jsonb,

    is_active           boolean NOT NULL DEFAULT true,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    verified_by         text,
    verified_at         timestamptz,
    notes               text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    -- (1) A rule attributed to a real book must say where in that book.
    CONSTRAINT rule_scholarly_needs_reference CHECK (
        source_book = 'TAFAHHUM_BASELINE'
        OR (source_reference IS NOT NULL AND length(trim(source_reference)) > 0)
    ),

    -- (2) A rule attributed to a real book must link the bibliographical record.
    CONSTRAINT rule_scholarly_needs_biblio CHECK (
        source_book = 'TAFAHHUM_BASELINE' OR biblio_source_id IS NOT NULL
    ),

    -- (3) Nothing becomes VERIFIED without a named human reviewer.
    CONSTRAINT rule_verified_needs_reviewer CHECK (
        verification_status <> 'VERIFIED'
        OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)
    ),

    -- (4) Only the SCHOLARLY_METHOD tier may carry a book attribution, and a
    --     SCHOLARLY_METHOD rule may never be baseline. This is what prevents a
    --     structural rule from quietly acquiring scholarly authority.
    CONSTRAINT rule_tier_matches_provenance CHECK (
        (tier = 'SCHOLARLY_METHOD' AND source_book <> 'TAFAHHUM_BASELINE')
        OR (tier <> 'SCHOLARLY_METHOD' AND source_book = 'TAFAHHUM_BASELINE')
    )
);

CREATE INDEX idx_rule_active ON scholarly_rule(tier, priority) WHERE is_active;
CREATE INDEX idx_rule_query_types ON scholarly_rule USING gin (applies_to_query_types);

CREATE TRIGGER trg_rule_updated BEFORE UPDATE ON scholarly_rule
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Rule application log — answers "why did Tafahhum retrieve this source?"
-- ---------------------------------------------------------------------------
CREATE TABLE query_run (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_query           text NOT NULL,
    user_language       language_code NOT NULL,
    pivot_query         text NOT NULL,
    detected_language   language_code,
    classified_type     query_type NOT NULL DEFAULT 'UNKNOWN',
    classification_confidence real,
    resolved_ayahs      jsonb NOT NULL DEFAULT '[]'::jsonb,
    answer_mode         text,
    evidence_count      int NOT NULL DEFAULT 0,
    unsupported_claim_count int NOT NULL DEFAULT 0,
    duration_ms         int,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE query_run_rule (
    query_run_id        uuid NOT NULL REFERENCES query_run(id) ON DELETE CASCADE,
    rule_id             uuid NOT NULL REFERENCES scholarly_rule(id) ON DELETE CASCADE,
    applied_at_stage    text NOT NULL,
    effect_summary      text,
    PRIMARY KEY (query_run_id, rule_id, applied_at_stage)
);

CREATE INDEX idx_query_run_created ON query_run(created_at DESC);
