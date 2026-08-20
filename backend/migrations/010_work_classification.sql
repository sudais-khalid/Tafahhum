-- 010_work_classification.sql — school, method, and era on a Tafsir work
--
-- Assigning a work to a school is a scholarly claim, not a neutral label. It is
-- contested for several major works, and getting it wrong misrepresents both the
-- author and whoever relies on the filter.
--
-- So classification is stored the same way every other claim in this system is:
-- with the source it came from, and a verification state that starts unverified.
-- A filter for "Sunni works" therefore means "works a named source classifies as
-- Sunni", which is a statement the system can actually support.

CREATE TYPE scholarly_tradition AS ENUM (
    'SUNNI',
    'SUNNI_SUFI',
    'SUNNI_SALAFI',
    'TWELVER_SHIA',
    'ZAYDI_SHIA',
    'MUTAZILA',
    'IBADI',
    'MODERNIST',
    'EARLY',          -- pre-dating the school divisions
    'UNCLASSIFIED'    -- no source consulted yet; never a guess
);

-- Broad methodological families. Also contested, also sourced.
CREATE TYPE tafsir_method AS ENUM (
    'BI_AL_MATHUR',     -- by transmitted report
    'BI_AL_RAY',        -- by considered opinion
    'FIQHI',            -- legal
    'LUGHAWI',          -- linguistic / grammatical
    'BALAGHI',          -- rhetorical
    'SUFI_ISHARI',      -- allusive
    'KALAMI',           -- theological
    'QIRAAT',           -- variant readings
    'GHARIB',           -- rare vocabulary
    'MIXED',
    'UNCLASSIFIED'
);

ALTER TABLE tafsir_work
    ADD COLUMN tradition scholarly_tradition NOT NULL DEFAULT 'UNCLASSIFIED',
    ADD COLUMN method tafsir_method NOT NULL DEFAULT 'UNCLASSIFIED',
    -- Where the classification came from. NULL means nothing asserted it.
    ADD COLUMN classification_source text,
    ADD COLUMN classification_source_url text,
    ADD COLUMN classification_status verification_status NOT NULL DEFAULT 'UNVERIFIED',
    ADD COLUMN classification_note text,
    -- Presentation order within a listing; lower sorts first.
    ADD COLUMN catalogue_rank int NOT NULL DEFAULT 500,
    -- Whether the work is offered in the default selection.
    ADD COLUMN is_default_source boolean NOT NULL DEFAULT false;

-- A classified work must say who classified it. Only UNCLASSIFIED may be silent.
ALTER TABLE tafsir_work ADD CONSTRAINT work_classification_needs_source CHECK (
    tradition = 'UNCLASSIFIED'
    OR (classification_source IS NOT NULL AND length(trim(classification_source)) > 0)
);

CREATE INDEX idx_work_tradition ON tafsir_work(tradition) WHERE corpus_state = 'PUBLISHED';
CREATE INDEX idx_work_method ON tafsir_work(method);
CREATE INDEX idx_work_catalogue ON tafsir_work(catalogue_rank, slug);

-- The list used as the classification source, registered like any other
-- bibliographical work so that a classification can be traced to it.
INSERT INTO biblio_source
    (slug, title_ar, title_en, genre, notes, verification_status)
VALUES (
    'wikipedia-list-of-tafsir-works',
    'قائمة مؤلفات التفسير',
    'List of tafsir works (Wikipedia)',
    'catalogue',
    'Tertiary reference used only to group works by school and method so a '
    'reader can filter the corpus. It is not a scholarly authority: every '
    'classification drawn from it is UNVERIFIED and awaits review against a '
    'tabaqat work. No interpretive claim rests on it.',
    'UNVERIFIED'
)
ON CONFLICT (slug) DO NOTHING;
