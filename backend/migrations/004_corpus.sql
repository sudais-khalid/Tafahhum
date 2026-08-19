-- 004_corpus.sql — scans, OCR, passages, ayah alignment, corrections
--
-- The page image is the primary visual evidence and is never discarded.
-- raw_text is never overwritten; corrections are additive and audited.

-- ---------------------------------------------------------------------------
-- Scanned page — one row per physical page image
-- ---------------------------------------------------------------------------
CREATE TABLE scan_page (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    edition_id      uuid NOT NULL REFERENCES edition(id) ON DELETE CASCADE,
    volume          int NOT NULL,
    page_label      text NOT NULL,       -- as printed; may be roman, or 'أ'
    page_number     int,                 -- numeric form when derivable
    image_index     int NOT NULL,        -- position in the scan sequence

    image_uri       text NOT NULL,       -- object-store key, not a blob
    image_width     int,
    image_height    int,
    image_sha256    text,

    ocr_engine      text,
    ocr_engine_version text,
    ocr_run_at      timestamptz,
    ocr_confidence  real CHECK (ocr_confidence IS NULL OR ocr_confidence BETWEEN 0 AND 1),
    ocr_raw_text    text,
    -- Word/line boxes, kept so a passage can be highlighted on the image.
    ocr_layout      jsonb,

    needs_review    boolean NOT NULL DEFAULT true,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (edition_id, volume, image_index)
);

CREATE INDEX idx_scan_page_edition ON scan_page(edition_id, volume, page_number);
CREATE INDEX idx_scan_page_review ON scan_page(needs_review) WHERE needs_review;

-- ---------------------------------------------------------------------------
-- Passage — the unit of retrieval and citation
-- ---------------------------------------------------------------------------
CREATE TABLE passage (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    edition_id          uuid NOT NULL REFERENCES edition(id) ON DELETE CASCADE,
    tafsir_work_id      uuid NOT NULL REFERENCES tafsir_work(id) ON DELETE CASCADE,
    author_id           uuid REFERENCES mufassir(id) ON DELETE SET NULL,

    -- Physical location. This is what a citation resolves to.
    volume              int,
    page_start          int,
    page_end            int,
    scan_page_id        uuid REFERENCES scan_page(id) ON DELETE SET NULL,
    sequence_index      bigint NOT NULL,   -- reading order within the edition

    -- Three parallel representations, never collapsed (ARCHITECTURE §6)
    raw_text            text NOT NULL,
    normalized_text     text NOT NULL,
    verified_text       text,

    evidence_kind       evidence_type NOT NULL DEFAULT 'MUFASSIR_INTERPRETATION',
    language            language_code NOT NULL DEFAULT 'ar',

    ocr_confidence      real CHECK (ocr_confidence IS NULL OR ocr_confidence BETWEEN 0 AND 1),
    citation_precision  verification_status NOT NULL DEFAULT 'UNVERIFIED',
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',

    -- Structured mentions, populated by extraction and confirmed by review.
    topics              text[] NOT NULL DEFAULT '{}',
    mentioned_people    text[] NOT NULL DEFAULT '{}',
    mentioned_books     text[] NOT NULL DEFAULT '{}',
    mentioned_qiraat    text[] NOT NULL DEFAULT '{}',

    -- Dense retrieval. 1024 dims = BGE-M3, the default multilingual embedder.
    embedding           vector(1024),
    embedding_model     text,
    embedded_at         timestamptz,

    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT passage_page_order CHECK (
        page_start IS NULL OR page_end IS NULL OR page_end >= page_start
    ),
    UNIQUE (edition_id, sequence_index)
);

-- Display text: prefer human-verified, fall back to raw. Never the normalized form,
-- which exists only for matching and has had orthographic detail stripped.
CREATE OR REPLACE FUNCTION passage_display_text(p passage) RETURNS text
LANGUAGE sql IMMUTABLE AS $fn$
    SELECT COALESCE(p.verified_text, p.raw_text);
$fn$;

ALTER TABLE passage ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('tafahhum_ar', normalized_text)) STORED;

CREATE INDEX idx_passage_fts ON passage USING gin (search_vector);
CREATE INDEX idx_passage_trgm ON passage USING gin (normalized_text gin_trgm_ops);
CREATE INDEX idx_passage_work ON passage(tafsir_work_id);
CREATE INDEX idx_passage_author ON passage(author_id);
CREATE INDEX idx_passage_edition_loc ON passage(edition_id, volume, page_start);
CREATE INDEX idx_passage_status ON passage(verification_status);
CREATE INDEX idx_passage_topics ON passage USING gin (topics);

-- HNSW for dense retrieval. Cosine distance matches normalized embeddings.
CREATE INDEX idx_passage_embedding ON passage
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TRIGGER trg_passage_updated BEFORE UPDATE ON passage
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Ayah alignment
--
-- One passage may cover several ayahs, and those ayahs need not be contiguous
-- (a Mufassir may treat 2:255 and 2:256 together, or discuss 2:255 while
-- commenting elsewhere). A join table models this honestly; an ayah_start /
-- ayah_end pair on the passage would not.
-- ---------------------------------------------------------------------------
CREATE TYPE alignment_kind AS ENUM (
    'PRIMARY',        -- the passage is the commentary on this ayah
    'DISCUSSED',      -- substantively discussed, not the head reference
    'CITED',          -- quoted in passing as evidence
    'CROSS_REFERENCE'
);

CREATE TABLE passage_ayah (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    passage_id      uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
    surah_number    int NOT NULL REFERENCES surah(number),
    ayah_start      int NOT NULL CHECK (ayah_start > 0),
    ayah_end        int NOT NULL CHECK (ayah_end > 0),
    alignment       alignment_kind NOT NULL DEFAULT 'PRIMARY',
    confidence      real CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    verification_status verification_status NOT NULL DEFAULT 'MACHINE_PROPOSED',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ayah_range_valid CHECK (ayah_end >= ayah_start),
    UNIQUE (passage_id, surah_number, ayah_start, ayah_end, alignment)
);

CREATE INDEX idx_passage_ayah_lookup
    ON passage_ayah(surah_number, ayah_start, ayah_end);
CREATE INDEX idx_passage_ayah_passage ON passage_ayah(passage_id);

-- Range-overlap index: finds every passage touching a queried ayah range.
CREATE INDEX idx_passage_ayah_range ON passage_ayah
    USING gist (surah_number, int4range(ayah_start, ayah_end, '[]'));

-- ---------------------------------------------------------------------------
-- Corrections — additive, never destructive
-- ---------------------------------------------------------------------------
CREATE TABLE passage_correction (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    passage_id      uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
    previous_text   text NOT NULL,
    corrected_text  text NOT NULL,
    reason          text,
    corrected_by    text NOT NULL,
    corrected_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_correction_passage ON passage_correction(passage_id, corrected_at DESC);

-- Guard: raw_text is immutable. A correction goes to verified_text and is logged.
CREATE OR REPLACE FUNCTION protect_raw_text() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.raw_text IS DISTINCT FROM OLD.raw_text THEN
        RAISE EXCEPTION
            'passage.raw_text is immutable (passage %). Write to verified_text and log a passage_correction.',
            OLD.id;
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_passage_raw_immutable BEFORE UPDATE ON passage
    FOR EACH ROW EXECUTE FUNCTION protect_raw_text();

-- ---------------------------------------------------------------------------
-- Passage translations — derived artefacts, always attributed (SOURCE_POLICY §9)
-- ---------------------------------------------------------------------------
CREATE TABLE passage_translation (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    passage_id      uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
    language        language_code NOT NULL,
    text            text NOT NULL,
    translator_kind text NOT NULL CHECK (translator_kind IN ('HUMAN', 'MACHINE')),
    translator_name text NOT NULL,
    model_name      text,
    reviewed_by     text,
    verification_status verification_status NOT NULL DEFAULT 'MACHINE_PROPOSED',
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (passage_id, language, translator_name)
);

CREATE INDEX idx_passage_tr ON passage_translation(passage_id, language);

-- ---------------------------------------------------------------------------
-- The only view user-facing retrieval is permitted to read.
--
-- Enforcing the fixture/verification exclusion here rather than in application
-- code means a forgotten WHERE clause in a new query path cannot leak test data
-- or unverified text into a user's result set.
-- ---------------------------------------------------------------------------
CREATE VIEW published_passage AS
SELECT p.*
FROM passage p
JOIN edition e ON e.id = p.edition_id
JOIN tafsir_work w ON w.id = p.tafsir_work_id
WHERE p.verification_status NOT IN ('FIXTURE', 'DISPUTED')
  AND e.corpus_state = 'PUBLISHED'
  AND w.corpus_state = 'PUBLISHED';
