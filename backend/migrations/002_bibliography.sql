-- 002_bibliography.sql — Mufassir, Tafsir work, Edition, bibliographical sources
-- A citation is meaningless without the edition it refers to (SOURCE_POLICY §5).

-- ---------------------------------------------------------------------------
-- Bibliographical source: a work *about* works. Nayl al-Sairin belongs here.
-- Every attributed claim in the catalogue points back to one of these.
-- ---------------------------------------------------------------------------
CREATE TABLE biblio_source (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                text NOT NULL UNIQUE,
    title_ar            text NOT NULL,
    title_en            text,
    author_name_ar      text,
    author_name_en      text,
    edition_note        text,
    publication_year    int,
    genre               text,          -- e.g. 'tabaqat_al_mufassirin'
    notes               text,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Mufassir
-- ---------------------------------------------------------------------------
CREATE TABLE mufassir (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                  text NOT NULL UNIQUE,

    name_ar               text NOT NULL,
    kunya_ar              text,
    nisba_ar              text,
    name_en               text,
    name_ur               text,
    alternative_names     text[] NOT NULL DEFAULT '{}',

    -- Hijri is authoritative; Gregorian is derived and may be approximate.
    birth_year_hijri      int,
    death_year_hijri      int,
    birth_year_gregorian  int,
    death_year_gregorian  int,
    date_precision        text,        -- exact | circa | range | unknown

    birth_place           text,
    death_place           text,
    region                text,
    period                historical_period NOT NULL DEFAULT 'UNKNOWN',

    madhhab               text,
    creed_tradition       text,
    methodology_note      text,
    primary_language      language_code NOT NULL DEFAULT 'ar',

    biography_note        text,
    verification_status   verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),

    -- A death year must follow a birth year, when both are known.
    CONSTRAINT mufassir_hijri_order CHECK (
        birth_year_hijri IS NULL OR death_year_hijri IS NULL
        OR death_year_hijri >= birth_year_hijri
    )
);

-- Which bibliographical works document this Mufassir, and where exactly.
CREATE TABLE mufassir_attestation (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mufassir_id         uuid NOT NULL REFERENCES mufassir(id) ON DELETE CASCADE,
    biblio_source_id    uuid NOT NULL REFERENCES biblio_source(id) ON DELETE RESTRICT,
    volume              int,
    page_start          int,
    page_end            int,
    entry_number        text,          -- tabaqat works often number their entries
    quoted_text_ar      text,
    note                text,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- Teacher / student / influence relations. Never inferred automatically (§16).
CREATE TABLE mufassir_relation (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_mufassir_id    uuid NOT NULL REFERENCES mufassir(id) ON DELETE CASCADE,
    to_mufassir_id      uuid NOT NULL REFERENCES mufassir(id) ON DELETE CASCADE,
    relation            text NOT NULL,  -- taught | studied_under | influenced_by | transmitted_from
    biblio_source_id    uuid REFERENCES biblio_source(id) ON DELETE SET NULL,
    source_reference    text,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT no_self_relation CHECK (from_mufassir_id <> to_mufassir_id),
    UNIQUE (from_mufassir_id, to_mufassir_id, relation)
);

-- ---------------------------------------------------------------------------
-- Tafsir work (the abstract work, independent of any printing)
-- ---------------------------------------------------------------------------
CREATE TABLE tafsir_work (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                    text NOT NULL UNIQUE,
    author_id               uuid REFERENCES mufassir(id) ON DELETE RESTRICT,

    title_ar                text NOT NULL,
    title_en                text,
    title_ur                text,
    alternative_titles      text[] NOT NULL DEFAULT '{}',
    short_name              text,          -- how scholars actually refer to it

    language                language_code NOT NULL DEFAULT 'ar',
    period                  historical_period NOT NULL DEFAULT 'UNKNOWN',
    composition_start_hijri int,
    composition_end_hijri   int,

    coverage                coverage_kind NOT NULL DEFAULT 'UNKNOWN',
    surahs_covered          int[] NOT NULL DEFAULT '{}',  -- empty = complete or unknown
    methodology_note        text,

    -- Attribution may be uncertain; that is a recordable state, not a blocker.
    attribution_confidence  verification_status NOT NULL DEFAULT 'UNVERIFIED',
    corpus_state            corpus_status NOT NULL DEFAULT 'DISCOVERED',
    verification_status     verification_status NOT NULL DEFAULT 'UNVERIFIED',
    notes                   text,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tafsir_work_attestation (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tafsir_work_id      uuid NOT NULL REFERENCES tafsir_work(id) ON DELETE CASCADE,
    biblio_source_id    uuid NOT NULL REFERENCES biblio_source(id) ON DELETE RESTRICT,
    volume              int,
    page_start          int,
    page_end            int,
    entry_number        text,
    quoted_text_ar      text,
    note                text,
    verification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Edition — a specific printing. Passages attach here, never to the work alone.
-- ---------------------------------------------------------------------------
CREATE TABLE edition (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                   text NOT NULL UNIQUE,
    tafsir_work_id         uuid NOT NULL REFERENCES tafsir_work(id) ON DELETE CASCADE,

    publisher              text,
    publication_place      text,
    publication_year       int,
    editor_name            text,          -- editor
    investigator_name      text,          -- muhaqqiq, where distinct from editor
    edition_number         text,
    volume_count           int,
    total_page_count       int,
    isbn                   text,

    scan_source            text,
    digital_source_url     text,
    -- Page label offset: printed page 1 may be image 17. Needed for scan links.
    page_image_offset      int NOT NULL DEFAULT 0,

    copyright_status       copyright_status NOT NULL DEFAULT 'UNKNOWN',
    license                text,
    source_license         text,
    redistribution_allowed boolean,
    commercial_use_allowed boolean,
    license_note           text,

    edition_quality_note   text,
    is_critical_edition    boolean,
    corpus_state           corpus_status NOT NULL DEFAULT 'DISCOVERED',
    verification_status    verification_status NOT NULL DEFAULT 'UNVERIFIED',
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT edition_volume_count_sane CHECK (volume_count IS NULL OR volume_count > 0)
);

CREATE INDEX idx_tafsir_work_author ON tafsir_work(author_id);
CREATE INDEX idx_edition_work ON edition(tafsir_work_id);
CREATE INDEX idx_mufassir_death ON mufassir(death_year_hijri);
CREATE INDEX idx_mufassir_period ON mufassir(period);
CREATE INDEX idx_mufassir_name_trgm ON mufassir USING gin (name_ar gin_trgm_ops);
CREATE INDEX idx_tafsir_title_trgm ON tafsir_work USING gin (title_ar gin_trgm_ops);
CREATE INDEX idx_mufassir_attest ON mufassir_attestation(mufassir_id, biblio_source_id);
CREATE INDEX idx_work_attest ON tafsir_work_attestation(tafsir_work_id, biblio_source_id);

CREATE TRIGGER trg_mufassir_updated BEFORE UPDATE ON mufassir
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_tafsir_updated BEFORE UPDATE ON tafsir_work
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_edition_updated BEFORE UPDATE ON edition
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_biblio_updated BEFORE UPDATE ON biblio_source
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
