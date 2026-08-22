-- 013_ayah_summary.sql — generated conclusions, and the evidence behind them
--
-- A summary of exegesis is itself exegesis, so this is the one place in the
-- system where text is written rather than quoted. Everything about the table
-- exists to keep that text tethered:
--
--   * it records exactly which passages were in front of the model
--   * it records which sentences were verified against those passages and which
--     were removed
--   * it is typed TAFAHHUM_SYNTHESIS and can never be cited as a source
--
-- If the verification fields ever look unimpressive, that is the point. A
-- summary with three unsupported sentences removed is more trustworthy than one
-- that claims perfection, because the removals are visible.

CREATE TABLE ayah_summary (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    surah_number        int NOT NULL REFERENCES surah(number),
    ayah_number         int NOT NULL,
    language            language_code NOT NULL,

    -- The generated text, after unsupported sentences have been removed.
    summary_text        text NOT NULL,
    -- What the model produced before verification, kept so a reviewer can see
    -- what was cut and judge whether the filter was right.
    raw_output          text NOT NULL,

    model_name          text NOT NULL,
    generator_version   text NOT NULL,

    -- Which works were in the selection when this was generated. The same ayah
    -- read with different sources is a different summary, not a stale one.
    source_work_slugs   text[] NOT NULL,
    -- The selection, sorted and joined, so the uniqueness key is a plain column.
    -- Deriving it in the index would need array_to_string, which is STABLE
    -- rather than IMMUTABLE and so cannot appear in an index expression.
    selection_key       text NOT NULL,
    -- The exact passages placed in front of the model.
    cited_passage_ids   uuid[] NOT NULL,

    sentences_generated int NOT NULL,
    sentences_kept      int NOT NULL,
    sentences_removed   int NOT NULL,
    -- Mean lexical overlap between each kept sentence and the passage it cites.
    mean_support        real,

    evidence_kind       evidence_type NOT NULL DEFAULT 'TAFAHHUM_SYNTHESIS',
    verification_status verification_status NOT NULL DEFAULT 'MACHINE_PROPOSED',
    reviewed_by         text,
    reviewed_at         timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),

    -- A summary is a synthesis by definition; nothing else may be stored here.
    CONSTRAINT summary_is_synthesis CHECK (evidence_kind = 'TAFAHHUM_SYNTHESIS'),
    -- It must name the passages it was built from. A summary with no evidence
    -- behind it is exactly what this system exists to prevent.
    CONSTRAINT summary_needs_evidence CHECK (cardinality(cited_passage_ids) > 0),
    CONSTRAINT summary_counts_agree CHECK (
        sentences_kept + sentences_removed = sentences_generated
    ),
    CONSTRAINT summary_verified_needs_reviewer CHECK (
        verification_status <> 'VERIFIED'
        OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
);

-- One current summary per ayah, language, and source selection.
CREATE UNIQUE INDEX idx_ayah_summary_key
    ON ayah_summary(surah_number, ayah_number, language, selection_key);

CREATE INDEX idx_ayah_summary_lookup ON ayah_summary(surah_number, ayah_number, language);
