-- 007_baseline_rules.sql — structural rules only
--
-- READ THIS BEFORE ADDING A RULE.
--
-- Every rule in this file is TAFAHHUM_BASELINE: it governs mechanical retrieval
-- behaviour and makes NO scholarly claim. None is attributed to any book, and
-- the CHECK constraints in 005_rules.sql forbid these tiers from carrying a book
-- attribution at all.
--
-- Rules grounded in a scholarly methodology belong in the SCHOLARLY_METHOD tier
-- and require: an ingested bibliographical source, a volume/page reference, and
-- a named human reviewer. That path is described in docs/SOURCE_POLICY.md §6.
-- There are deliberately ZERO such rules at present, because no bibliographical
-- source has been ingested and verified yet.
--
-- Writing plausible-sounding methodological rules and labelling them as derived
-- from a book that has not been read is the exact fabrication this system exists
-- to prevent — and it would be undetectable to a user, because the citation
-- would look correct.

INSERT INTO scholarly_rule
    (rule_key, name, description, tier, priority, source_book,
     applies_to_query_types, effects, verification_status, notes)
VALUES

-- ---------------------------------------------------------------------------
-- Tier 1: SYSTEM_INTEGRITY
-- ---------------------------------------------------------------------------
('integrity.no_unsourced_claim',
 'Every claim requires an evidence passage',
 'A statement in a generated answer must map to at least one retrieved passage. '
 'Claims without supporting evidence are removed before the answer is returned.',
 'SYSTEM_INTEGRITY', 10, 'TAFAHHUM_BASELINE',
 '{}', '{"enforce": "citation_verification"}'::jsonb,
 'UNVERIFIED',
 'Structural invariant, not a scholarly position.'),

('integrity.insufficient_evidence_is_an_answer',
 'Report insufficient evidence rather than filling the gap',
 'When retrieval returns no qualifying evidence, the system states that the '
 'corpus does not currently support an answer. It does not widen the query, '
 'lower the verification threshold, or answer from general knowledge.',
 'SYSTEM_INTEGRITY', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"on_empty_evidence": "declare_insufficient"}'::jsonb,
 'UNVERIFIED',
 NULL),

('integrity.evidence_types_stay_distinct',
 'Evidence kinds are never silently merged',
 'Quranic text, Hadith, Companion and Tabii reports, Mufassir interpretation, '
 'later scholarship, modern analysis, and Tafahhum synthesis each carry an '
 'explicit label in the response.',
 'SYSTEM_INTEGRITY', 30, 'TAFAHHUM_BASELINE',
 '{}', '{"label_evidence_type": true}'::jsonb,
 'UNVERIFIED',
 NULL),

-- ---------------------------------------------------------------------------
-- Tier 2: SOURCE_PROVENANCE
-- ---------------------------------------------------------------------------
('provenance.published_only',
 'Retrieval reads only published corpus material',
 'User-facing retrieval reads the published_passage view, which excludes fixture '
 'and disputed rows and any work or edition not in the PUBLISHED state.',
 'SOURCE_PROVENANCE', 10, 'TAFAHHUM_BASELINE',
 '{}', '{"source_view": "published_passage"}'::jsonb,
 'UNVERIFIED',
 'Enforced in the database, not only here.'),

('provenance.citation_carries_edition',
 'A citation names its edition',
 'Passages cite the edition they were ingested from. Where the edition has no '
 'identified print counterpart, the response states that no page-level citation '
 'is available rather than omitting the limitation.',
 'SOURCE_PROVENANCE', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"require_edition_in_citation": true, "disclose_missing_page": true}'::jsonb,
 'UNVERIFIED',
 NULL),

('provenance.quotation_is_never_translated_silently',
 'Source text is shown in its own language',
 'An Arabic passage is presented in Arabic. Any rendering into the user language '
 'is labelled a translation, attributed, and shown alongside the original rather '
 'than in place of it.',
 'SOURCE_PROVENANCE', 30, 'TAFAHHUM_BASELINE',
 '{}', '{"preserve_source_language": true}'::jsonb,
 'UNVERIFIED',
 NULL),

-- ---------------------------------------------------------------------------
-- Tier 4: QUERY_STRATEGY
-- ---------------------------------------------------------------------------
('strategy.independent_retrieval_per_work',
 'Each work is retrieved independently',
 'Candidate passages are ranked within each work before being combined, so a '
 'lengthy commentary cannot displace a terse one. Retrieval for one Mufassir '
 'never conditions retrieval for another.',
 'QUERY_STRATEGY', 10, 'TAFAHHUM_BASELINE',
 '{AYAH_TAFSIR,COMPARATIVE,THEMATIC,SCHOLARLY_DISAGREEMENT}',
 '{"partition_by": "work", "per_work_cap": 3}'::jsonb,
 'UNVERIFIED',
 'Purely mechanical: prevents commentary length from acting as relevance.'),

('strategy.hybrid_retrieval',
 'Sparse and dense retrieval both run',
 'Exact and semantic retrieval answer different needs — exact phrases, names and '
 'quotations versus differently-worded concepts — so both run and are fused by '
 'reciprocal rank rather than by comparing incomparable scores.',
 'QUERY_STRATEGY', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"strategies": ["structural", "sparse", "dense"], "fusion": "rrf"}'::jsonb,
 'UNVERIFIED',
 NULL),

('strategy.comparative_isolates_each_source',
 'A comparative query retrieves each named work separately',
 'When a query names several works, each is retrieved with its own query so that '
 'no source biases the retrieval of another. Results are presented side by side.',
 'QUERY_STRATEGY', 30, 'TAFAHHUM_BASELINE',
 '{COMPARATIVE}', '{"isolate_named_works": true}'::jsonb,
 'UNVERIFIED',
 NULL),

('strategy.historical_orders_by_death_year',
 'Historical queries order by author death year',
 'Chronological presentation sorts by the author Hijri death year where known. '
 'Works whose author date is unknown are shown in a separate undated group '
 'rather than being assigned a position.',
 'QUERY_STRATEGY', 40, 'TAFAHHUM_BASELINE',
 '{HISTORICAL}', '{"order_by": "author_death_year_hijri", "unknown": "separate_group"}'::jsonb,
 'UNVERIFIED',
 'Ordering is a display decision; it asserts no periodisation scheme.'),

-- ---------------------------------------------------------------------------
-- Tier 5: EVIDENCE_QUALITY
-- ---------------------------------------------------------------------------
('evidence.rank_is_not_authority',
 'Retrieval rank confers no scholarly weight',
 'Passage count, similarity score, and recency are ranking signals only. The '
 'system never resolves a disagreement between Mufassirun by preferring the '
 'position with more retrieved passages or a higher score.',
 'EVIDENCE_QUALITY', 10, 'TAFAHHUM_BASELINE',
 '{}', '{"forbid_score_as_authority": true}'::jsonb,
 'UNVERIFIED',
 'The most important rule in this tier.'),

('evidence.surface_confidence_dimensions',
 'Reliability is reported per dimension',
 'OCR confidence, text verification, citation precision, and attribution '
 'confidence are reported separately. They are never averaged into a single '
 'accuracy score, which would destroy the distinction between them.',
 'EVIDENCE_QUALITY', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"report_dimensions": ["ocr_confidence", "verification_status", "citation_precision", "attribution_confidence"]}'::jsonb,
 'UNVERIFIED',
 NULL),

-- ---------------------------------------------------------------------------
-- Tier 6: RESPONSE_STRUCTURE
-- ---------------------------------------------------------------------------
('response.preserve_disagreement',
 'Disagreement is presented, not resolved',
 'Where retrieved passages support differing interpretations, each position is '
 'presented with its own sources. A synthesis may follow, labelled as Tafahhum '
 'synthesis, but no position is presented as settled unless the sources say so.',
 'RESPONSE_STRUCTURE', 10, 'TAFAHHUM_BASELINE',
 '{}', '{"group_by_position": true, "never_manufacture_consensus": true}'::jsonb,
 'UNVERIFIED',
 NULL),

('response.separate_quran_from_commentary',
 'Quranic text is presented apart from commentary',
 'The ayah under discussion is displayed distinctly from the interpretations of '
 'it, so a reader can never mistake commentary for revealed text.',
 'RESPONSE_STRUCTURE', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"separate_ayah_block": true}'::jsonb,
 'UNVERIFIED',
 NULL),

-- ---------------------------------------------------------------------------
-- Tier 7: LANGUAGE_GENERATION
-- ---------------------------------------------------------------------------
('language.arabic_pivot',
 'Retrieval runs in Arabic regardless of the user language',
 'Queries in English or Urdu are carried into Arabic before retrieval, because '
 'the corpus is Arabic. Presentation is rendered back into the user language.',
 'LANGUAGE_GENERATION', 10, 'TAFAHHUM_BASELINE',
 '{}', '{"pivot": "ar", "user_languages": ["ar", "en", "ur"]}'::jsonb,
 'UNVERIFIED',
 NULL),

('language.translation_is_labelled',
 'Machine translation is disclosed',
 'Text rendered by machine translation is labelled as such, with the model named, '
 'and is never presented as a quotation from a source.',
 'LANGUAGE_GENERATION', 20, 'TAFAHHUM_BASELINE',
 '{}', '{"label_machine_translation": true}'::jsonb,
 'UNVERIFIED',
 NULL)

ON CONFLICT (rule_key) DO NOTHING;
