-- 011_ayah_phrases.sql — clause structure of an ayah, and passage alignment
--
-- Reading tafsir means taking an ayah one clause at a time and hearing what was
-- said about each. Grouping passages by book only helps a reader who already
-- knows the books; grouping by clause helps anyone who arrived with a question
-- about the ayah.
--
-- The clause boundaries are derived from the corpus, not from a grammar model:
-- commentators bracket the clause they are treating, and the spans several
-- commentaries return to are the divisions the tradition actually uses. The
-- support count is kept so a reader can see how well attested a division is.

CREATE TABLE ayah_phrase (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    surah_number    int NOT NULL REFERENCES surah(number),
    ayah_number     int NOT NULL,
    phrase_index    int NOT NULL,
    start_word      int NOT NULL,
    end_word        int NOT NULL,
    text_ar         text NOT NULL,
    normalized      text NOT NULL,
    -- How many distinct passages quoted this span.
    support         int NOT NULL DEFAULT 0,
    -- Derived data: recomputable from passages at any time, so it is safe to
    -- rebuild after ingesting more commentaries.
    derived_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (surah_number, ayah_number, phrase_index),
    CONSTRAINT phrase_word_order CHECK (end_word >= start_word)
);

CREATE INDEX idx_ayah_phrase_lookup ON ayah_phrase(surah_number, ayah_number, phrase_index);

CREATE TYPE phrase_alignment_basis AS ENUM (
    'QUOTED',    -- the passage bracketed this clause; strong evidence
    'OVERLAP'    -- matched by word overlap; weaker, and labelled as such
);

CREATE TABLE passage_phrase (
    passage_id      uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
    phrase_id       uuid NOT NULL REFERENCES ayah_phrase(id) ON DELETE CASCADE,
    basis           phrase_alignment_basis NOT NULL,
    matched_words   int NOT NULL,
    confidence      real NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    -- Extracted opening line, so a reader can scan before committing to read.
    -- Extracted from the passage, never written: it is the passage's own words.
    gist            text,
    PRIMARY KEY (passage_id, phrase_id)
);

CREATE INDEX idx_passage_phrase_phrase ON passage_phrase(phrase_id, confidence DESC);
CREATE INDEX idx_passage_phrase_passage ON passage_phrase(passage_id);
