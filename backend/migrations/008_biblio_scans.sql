-- 008_biblio_scans.sql — scanned pages for bibliographical sources, and OCR text
--
-- A tabaqat work is a source *about* sources. Its pages need the same scan and
-- OCR treatment as a Tafsir edition, but it is not a Tafsir edition and forcing
-- it to be one would put a bibliographical work into the Tafsir catalogue.
--
-- scan_page therefore gains a second possible parent, with exactly one required.

ALTER TABLE scan_page
    ADD COLUMN biblio_source_id uuid REFERENCES biblio_source(id) ON DELETE CASCADE;

-- edition_id was NOT NULL; a page now belongs to an edition or a biblio source.
ALTER TABLE scan_page ALTER COLUMN edition_id DROP NOT NULL;

ALTER TABLE scan_page ADD CONSTRAINT scan_page_one_parent CHECK (
    (edition_id IS NOT NULL AND biblio_source_id IS NULL)
    OR (edition_id IS NULL AND biblio_source_id IS NOT NULL)
);

-- The unique key was (edition_id, volume, image_index); it must now also cover
-- pages belonging to a bibliographical source. Dropping the constraint drops the
-- index it owns, so the constraint must go first.
ALTER TABLE scan_page DROP CONSTRAINT IF EXISTS scan_page_edition_id_volume_image_index_key;
CREATE UNIQUE INDEX idx_scan_page_edition_seq
    ON scan_page(edition_id, volume, image_index) WHERE edition_id IS NOT NULL;
CREATE UNIQUE INDEX idx_scan_page_biblio_seq
    ON scan_page(biblio_source_id, volume, image_index) WHERE biblio_source_id IS NOT NULL;

CREATE INDEX idx_scan_page_biblio ON scan_page(biblio_source_id, page_number);

-- ---------------------------------------------------------------------------
-- OCR text, in the same three representations used everywhere else.
-- ocr_raw_text already exists and stays immutable.
-- ---------------------------------------------------------------------------
ALTER TABLE scan_page
    ADD COLUMN ocr_normalized_text text,
    ADD COLUMN ocr_verified_text   text,
    ADD COLUMN language            language_code NOT NULL DEFAULT 'ar',
    ADD COLUMN script              text,          -- 'naskh' | 'nastaliq' | 'mixed'
    -- Engine-reported confidence is not comparable across engines, so the engine
    -- that produced a value is recorded beside it.
    ADD COLUMN ocr_engine_note     text,
    ADD COLUMN reviewed_by         text,
    ADD COLUMN reviewed_at         timestamptz;

-- OCR output is never overwritten, for the same reason passage.raw_text is not:
-- a correction must remain traceable to what the engine actually produced.
CREATE OR REPLACE FUNCTION protect_ocr_raw_text() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF OLD.ocr_raw_text IS NOT NULL
       AND NEW.ocr_raw_text IS DISTINCT FROM OLD.ocr_raw_text THEN
        RAISE EXCEPTION
            'scan_page.ocr_raw_text is immutable once written (page %). Write to ocr_verified_text.',
            OLD.id;
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_scan_ocr_immutable BEFORE UPDATE ON scan_page
    FOR EACH ROW EXECUTE FUNCTION protect_ocr_raw_text();

ALTER TABLE scan_page ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('tafahhum_ar', coalesce(ocr_verified_text, ocr_normalized_text, ''))
    ) STORED;
CREATE INDEX idx_scan_page_fts ON scan_page USING gin (search_vector);

-- ---------------------------------------------------------------------------
-- Register Nayl al-Sairin. The record exists before any page is read, so that
-- attestations always have something to point at and the corpus state is
-- explicit about how far processing has got.
-- ---------------------------------------------------------------------------
INSERT INTO biblio_source
    (slug, title_ar, title_en, genre, notes, verification_status)
VALUES (
    'nayl-al-sairin',
    'نيل السائرين في طبقات المفسرين',
    'Nayl al-Sairin fi Tabaqat al-Mufassirin',
    'tabaqat_al_mufassirin',
    'Urdu-language tabaqat work on the Mufassirun. The scanned copy held is a '
    'lithographed Nastaliq text at roughly 70 DPI, which conventional OCR cannot '
    'read reliably; see docs/OCR.md. Every extracted entry requires human review '
    'before any claim is attributed to this work.',
    'UNVERIFIED'
)
ON CONFLICT (slug) DO NOTHING;
