-- 012_phrase_openings.sql — mark passages that open a clause's discussion
--
-- Chunking splits a commentary at a size boundary, not at a clause boundary, so
-- many chunks are continuations: an isnad tail, a line of cited poetry, the
-- middle of an argument. Those align to a clause because they mention its words,
-- but they are unreadable on their own and misrepresent what the commentator
-- said about that clause.
--
-- A chunk that *opens* a discussion announces itself: it begins with a lemma
-- header, or brackets the clause near its start. Marking that lets the reading
-- view show where each commentator begins, and keep the continuations available
-- without leading with them.

ALTER TABLE passage_phrase
    ADD COLUMN opens_discussion boolean NOT NULL DEFAULT false;

CREATE INDEX idx_passage_phrase_opening
    ON passage_phrase(phrase_id, opens_discussion DESC, confidence DESC);
