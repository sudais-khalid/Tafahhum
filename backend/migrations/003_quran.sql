-- 003_quran.sql — Quranic structure and text
--
-- Quranic text is itself a sourced artefact: it carries an edition/riwayah
-- attribution like any other text in the corpus. There is no "default" Quran text
-- floating free of provenance.

CREATE TABLE surah (
    number          int PRIMARY KEY CHECK (number BETWEEN 1 AND 114),
    name_ar         text NOT NULL,
    name_ar_plain   text NOT NULL,      -- normalized, diacritic-free, for matching
    name_en         text NOT NULL,
    name_en_translit text NOT NULL,     -- e.g. 'Al-Baqarah'
    name_ur         text,
    meaning_en      text,
    ayah_count      int NOT NULL CHECK (ayah_count > 0),
    revelation_place text NOT NULL CHECK (revelation_place IN ('MECCAN', 'MEDINAN')),
    revelation_order int
);

-- A specific text tradition of the Quran (e.g. Hafs an Asim, Warsh an Nafi).
CREATE TABLE quran_text_source (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            text NOT NULL UNIQUE,
    name_ar         text NOT NULL,
    name_en         text NOT NULL,
    riwayah         text,
    script_style    text,               -- 'uthmani' | 'imlaei' | 'simple'
    source_url      text,
    license         text,
    copyright_status copyright_status NOT NULL DEFAULT 'UNKNOWN',
    is_default      boolean NOT NULL DEFAULT false,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Exactly one default text source may exist.
CREATE UNIQUE INDEX idx_quran_single_default ON quran_text_source((true)) WHERE is_default;

CREATE TABLE ayah (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    text_source_id  uuid NOT NULL REFERENCES quran_text_source(id) ON DELETE CASCADE,
    surah_number    int NOT NULL REFERENCES surah(number),
    ayah_number     int NOT NULL CHECK (ayah_number > 0),

    text_uthmani    text NOT NULL,      -- as printed, with full diacritics
    text_normalized text NOT NULL,      -- diacritic-free, orthographically normalized

    juz             int CHECK (juz BETWEEN 1 AND 30),
    hizb            int,
    rub             int,
    manzil          int,
    ruku            int,
    page_madani     int,                -- Madani mushaf page
    sajdah          boolean NOT NULL DEFAULT false,

    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (text_source_id, surah_number, ayah_number)
);

-- Translations of the Quran are *derived artefacts*, stored separately and always
-- attributed. They are never substituted for the Arabic in a citation.
CREATE TABLE ayah_translation (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    surah_number    int NOT NULL REFERENCES surah(number),
    ayah_number     int NOT NULL,
    language        language_code NOT NULL,
    translator_name text NOT NULL,
    translation_slug text NOT NULL,
    text            text NOT NULL,
    source_url      text,
    license         text,
    copyright_status copyright_status NOT NULL DEFAULT 'UNKNOWN',
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (translation_slug, surah_number, ayah_number)
);

CREATE INDEX idx_ayah_location ON ayah(surah_number, ayah_number);
CREATE INDEX idx_ayah_juz ON ayah(juz);
CREATE INDEX idx_ayah_page ON ayah(page_madani);
CREATE INDEX idx_ayah_tr_lang ON ayah_translation(language, surah_number, ayah_number);

-- Full-text index over the normalized Quranic text.
ALTER TABLE ayah ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('tafahhum_ar', text_normalized)) STORED;
CREATE INDEX idx_ayah_fts ON ayah USING gin (search_vector);
CREATE INDEX idx_ayah_trgm ON ayah USING gin (text_normalized gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Named ayah groups: 'Ayat al-Kursi', 'the last two ayahs of al-Baqarah', etc.
-- These let a user ask by name rather than by numeric reference.
-- ---------------------------------------------------------------------------
CREATE TABLE ayah_alias (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alias_ar        text,
    alias_en        text,
    alias_ur        text,
    alias_normalized text NOT NULL,     -- matching key
    surah_number    int NOT NULL REFERENCES surah(number),
    ayah_start      int NOT NULL,
    ayah_end        int NOT NULL,
    note            text,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    CONSTRAINT alias_range_valid CHECK (ayah_end >= ayah_start)
);

CREATE INDEX idx_ayah_alias_norm ON ayah_alias USING gin (alias_normalized gin_trgm_ops);
