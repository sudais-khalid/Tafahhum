"""Unit tests for classification, the rule engine, pivoting, and chunking.

These run without a database. Database-backed behaviour is covered in
test_integration.py, which is marked `db`.
"""

from __future__ import annotations

import pytest

from tafahhum.core.enums import BASELINE_SOURCE_BOOK, Language, QueryType, RuleTier
from tafahhum.corpus.chunking import MAX_CHARS, chunk_commentary
from tafahhum.language.pivot import LexiconTranslator, to_pivot
from tafahhum.rules.classify import classify
from tafahhum.rules.engine import Rule, build_plan

WORK_TERMS = {
    "tabari": "tabari-jami-al-bayan",
    "qurtubi": "qurtubi-al-jami-li-ahkam",
    "kathir": "ibn-kathir-tafsir-al-quran-al-azim",
}


class TestClassification:
    def test_ayah_tafsir(self):
        c = classify("What do the Tafasir say about 2:255?", known_work_terms=WORK_TERMS)
        assert c.query_type is QueryType.AYAH_TAFSIR
        assert [str(r) for r in c.refs] == ["2:255"]

    def test_two_named_works_is_comparative(self):
        """A signal beats a keyword: naming two works is a comparison."""
        c = classify("Tabari and Qurtubi on 2:255", known_work_terms=WORK_TERMS)
        assert c.query_type is QueryType.COMPARATIVE
        assert len(c.named_works) == 2

    def test_comparative_keyword(self):
        c = classify("compare the commentaries on 2:255", known_work_terms=WORK_TERMS)
        assert c.query_type is QueryType.COMPARATIVE

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("what is the occasion of revelation for 2:255", QueryType.ASBAB_AL_NUZUL),
            ("variant readings of 2:255", QueryType.QIRAAT),
            ("the legal ruling in 2:256", QueryType.FIQH),
            ("how did interpretation develop through history", QueryType.HISTORICAL),
            ("where do the scholars disagree on 2:255", QueryType.SCHOLARLY_DISAGREEMENT),
            ("the grammar of 2:255", QueryType.LINGUISTIC),
        ],
    )
    def test_topical_types_outrank_generic_tafsir(self, text, expected):
        """A legal question about an ayah is not the same as a tafsir request."""
        assert classify(text, known_work_terms=WORK_TERMS).query_type is expected

    def test_arabic_query(self):
        c = classify("ما سبب نزول هذه الآية", known_work_terms=WORK_TERMS)
        assert c.query_type is QueryType.ASBAB_AL_NUZUL

    def test_urdu_query(self):
        c = classify("آیت الکرسی کی تفسیر کیا ہے؟", known_work_terms=WORK_TERMS)
        assert [str(r) for r in c.refs] == ["2:255"]

    def test_unknown_when_no_signal(self):
        assert classify("x", known_work_terms={}).query_type is QueryType.UNKNOWN

    def test_deterministic(self):
        text = "compare Tabari and Qurtubi on 2:255"
        a = classify(text, known_work_terms=WORK_TERMS)
        b = classify(text, known_work_terms=WORK_TERMS)
        assert (a.query_type, a.confidence, a.named_works) == (
            b.query_type, b.confidence, b.named_works
        )


def make_rule(key, tier, effects, source_book=BASELINE_SOURCE_BOOK, priority=100):
    return Rule(
        rule_key=key, name=key, description="", tier=tier, priority=priority,
        source_book=source_book, source_reference=None, verification_status="UNVERIFIED",
        applies_to=[], effects=effects, required_source_slugs=[],
        preferred_source_slugs=[], excluded_source_slugs=[],
    )


class TestRuleEngine:
    def test_higher_tier_wins(self):
        """The core guarantee: a lower tier cannot relax a higher tier's decision."""
        rules = [
            make_rule("integrity", RuleTier.SYSTEM_INTEGRITY, {"per_work_cap": 3}),
            make_rule("formatting", RuleTier.RESPONSE_STRUCTURE, {"per_work_cap": 99}),
        ]
        plan = build_plan(rules, QueryType.AYAH_TAFSIR)
        assert plan.per_work_cap == 3

    def test_lower_tier_may_set_untouched_keys(self):
        rules = [
            make_rule("integrity", RuleTier.SYSTEM_INTEGRITY, {"per_work_cap": 3}),
            make_rule("strategy", RuleTier.QUERY_STRATEGY, {"isolate_named_works": True}),
        ]
        plan = build_plan(rules, QueryType.COMPARATIVE)
        assert plan.per_work_cap == 3
        assert plan.isolate_named_works is True

    def test_baseline_rule_is_not_scholarly(self):
        rule = make_rule("r", RuleTier.QUERY_STRATEGY, {})
        assert not rule.is_scholarly
        assert "no scholarly claim" in rule.provenance

    def test_scholarly_rule_reports_its_source(self):
        rule = make_rule("r", RuleTier.SCHOLARLY_METHOD, {}, source_book="Some Book")
        assert rule.is_scholarly
        assert "Some Book" in rule.provenance

    def test_explain_exposes_provenance(self):
        plan = build_plan([make_rule("r", RuleTier.QUERY_STRATEGY, {})], QueryType.UNKNOWN)
        assert plan.explain()[0]["provenance"]


class TestPivot:
    def test_arabic_passes_through(self):
        r = to_pivot("ما معنى الحي القيوم", Language.AR)
        assert r.pivot_text == "ما معنى الحي القيوم"
        assert r.method == "passthrough"

    def test_english_maps_domain_terms(self):
        r = to_pivot("what is the occasion of revelation", Language.EN)
        assert "سبب النزول" in r.pivot_text

    def test_multiword_term_beats_its_parts(self):
        """'occasion of revelation' must not be consumed as 'revelation'."""
        r = to_pivot("occasion of revelation", Language.EN)
        assert "سبب النزول" in r.pivot_text
        assert r.pivot_text.strip() == "سبب النزول"

    def test_quoted_arabic_is_preserved(self):
        r = to_pivot("what does الحي القيوم mean", Language.EN)
        assert "الحي القيوم" in r.pivot_text

    def test_urdu_keeps_original_script_and_adds_arabic(self):
        r = to_pivot("آیت الکرسی کی تفسیر", Language.UR)
        assert "تفسير" in r.pivot_text

    def test_untranslatable_query_is_disclosed(self):
        r = to_pivot("hello there friend", Language.EN)
        assert r.pivot_text == ""
        assert r.note and "No Arabic search terms" in r.note

    def test_translation_is_disclosed(self):
        r = to_pivot("occasion of revelation", Language.EN)
        assert r.note and "mapped into Arabic" in r.note

    def test_translator_is_named(self):
        assert LexiconTranslator().name


class TestChunking:
    def test_empty_input(self):
        assert chunk_commentary("") == []

    def test_short_text_is_one_chunk(self):
        assert len(chunk_commentary("قال أبو جعفر: هذا تفسير قصير.")) == 1

    def test_long_text_is_split(self):
        text = "\n\n".join(["فقرة طويلة من التفسير. " * 20] * 10)
        chunks = chunk_commentary(text)
        assert len(chunks) > 1

    def test_no_chunk_wildly_exceeds_max(self):
        text = "\n\n".join(["نص تفسيري. " * 30] * 20)
        for c in chunk_commentary(text):
            assert c.char_count <= MAX_CHARS * 1.5

    def test_chunks_carry_all_three_representations(self):
        c = chunk_commentary("قَالَ أَبُو جَعْفَرٍ: الْحَيُّ الْقَيُّومُ")[0]
        assert c.raw_text and c.display_text and c.normalized_text
        # The matching form strips what display keeps.
        assert c.normalized_text != c.display_text

    def test_indices_are_sequential(self):
        text = "\n\n".join(["نص. " * 40] * 8)
        assert [c.index for c in chunk_commentary(text)] == list(
            range(len(chunk_commentary(text)))
        )

    def test_trailing_scrap_is_folded_in(self):
        text = "\n\n".join(["نص طويل جدا. " * 40, "قصير"])
        chunks = chunk_commentary(text)
        assert all(c.char_count >= 100 for c in chunks)
