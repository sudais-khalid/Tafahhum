"""The reference list and dual-language presentation.

These pin the two properties a reader's trust rests on: that every passage shown
is traceable to a numbered source with full provenance, and that a translation
never displaces the text it was made from.
"""

from __future__ import annotations

import psycopg
import pytest

from tafahhum.api.schemas import serialise
from tafahhum.core.config import get_settings
from tafahhum.core.enums import Language
from tafahhum.language.translate import Translation, fetch_many
from tafahhum.core.enums import VerificationStatus
from tafahhum.pipeline import QueryRequest, run_query

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(get_settings().dsn, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError as exc:
        pytest.skip(f"database unavailable: {exc}")
    with c:
        yield c


@pytest.fixture(scope="module")
def result_en(conn):
    pkg = run_query(
        conn, QueryRequest(text="What do the Tafasir say about 2:255?", user_language=Language.EN)
    )
    if pkg.is_empty:
        pytest.skip("corpus not seeded")
    return serialise(pkg)


@pytest.fixture(scope="module")
def result_ur(conn):
    pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.UR))
    if pkg.is_empty:
        pytest.skip("corpus not seeded")
    return serialise(pkg)


class TestReferenceList:
    def test_every_work_gets_a_reference(self, result_en):
        assert len(result_en.references) == len(
            [w for w in result_en.works if w.passages]
        )

    def test_references_are_numbered_from_one(self, result_en):
        numbers = [r.number for r in result_en.references]
        assert numbers == list(range(1, len(numbers) + 1))

    def test_every_passage_points_at_a_real_reference(self, result_en):
        """A passage with no resolvable source would be uncitable."""
        valid = {r.number for r in result_en.references}
        for work in result_en.works:
            for p in work.passages:
                assert p.reference_number in valid

    def test_passage_reference_matches_its_work(self, result_en):
        by_number = {r.number: r.work_slug for r in result_en.references}
        for work in result_en.works:
            for p in work.passages:
                assert by_number[p.reference_number] == work.work_slug

    def test_reference_carries_full_provenance(self, result_en):
        """A reader must not need a second request to judge a source."""
        for r in result_en.references:
            assert r.work_title_ar
            assert r.author_name_ar
            assert r.edition_slug
            assert r.copyright_status
            assert r.full_citation
            assert r.passages_cited > 0

    def test_passage_counts_sum_to_the_result(self, result_en):
        assert sum(r.passages_cited for r in result_en.references) == result_en.passage_count

    def test_unknown_dates_are_reported_not_hidden(self, result_en):
        """No death year is ingested yet, so every reference must say so."""
        for r in result_en.references:
            if r.author_death_year_hijri is None:
                assert r.author_dates_verified is False

    def test_missing_page_citation_is_visible_per_source(self, result_en):
        for r in result_en.references:
            assert r.resolves_to_page is False
            assert "no page-level citation" in r.full_citation


class TestQuranicText:
    def test_arabic_is_always_present(self, result_en, result_ur):
        for res in (result_en, result_ur):
            assert res.ayahs
            assert res.ayahs[0].text_uthmani

    def test_english_gets_named_translators(self, result_en):
        translations = result_en.ayahs[0].translations
        assert translations
        assert all(t.translator_name for t in translations)
        assert all(t.language == "en" for t in translations)

    def test_urdu_gets_named_translators(self, result_ur):
        translations = result_ur.ayahs[0].translations
        assert translations
        assert all(t.language == "ur" for t in translations)

    def test_quran_translations_are_human_editions(self, result_en):
        """Revealed text is never machine-translated.

        Ayah translations carry a translator name and a translation slug and have
        no model field at all — the type cannot express a machine rendering.
        """
        for t in result_en.ayahs[0].translations:
            assert t.translation_slug
            assert not hasattr(t, "model_name")


class TestDualLanguagePassages:
    def test_source_text_stays_in_its_own_language(self, result_ur):
        """Selecting Urdu must not replace the Arabic a Mufassir wrote."""
        for work in result_ur.works:
            for p in work.passages:
                assert p.text_language == "ar"
                assert p.text

    def test_arabic_reader_gets_no_translation_field_populated(self, conn):
        """Translating Arabic into Arabic is never attempted."""
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.AR))
        out = serialise(pkg)
        assert all(
            p.translation is None for w in out.works for p in w.passages
        )
        assert out.untranslated_passage_ids == []

    def test_untranslated_passages_are_listed_for_the_client(self, result_en):
        """The client needs to know exactly what to request, not guess."""
        ids = {p.passage_id for w in result_en.works for p in w.passages}
        assert set(result_en.untranslated_passage_ids) <= ids

    def test_translation_coverage_is_reported(self, result_en):
        assert 0.0 <= result_en.translation_coverage <= 1.0


class TestTranslationCache:
    def test_fetch_many_returns_empty_for_no_ids(self, conn):
        assert fetch_many(conn, [], Language.EN) == {}

    def test_fetch_many_is_keyed_by_passage(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM passage LIMIT 2")
            ids = [str(r["id"]) for r in cur.fetchall()]
        if len(ids) < 2:
            pytest.skip("corpus not seeded")

        from tafahhum.language.translate import store

        try:
            for i, pid in enumerate(ids):
                store(
                    conn, pid,
                    Translation(
                        text=f"sample {i}", language=Language.EN,
                        translator_kind="MACHINE", translator_name="test-fetch-many",
                        model_name="m",
                        verification_status=VerificationStatus.MACHINE_PROPOSED,
                    ),
                )
            found = fetch_many(conn, ids, Language.EN)
            assert set(found) == set(ids)
            assert found[ids[0]].text == "sample 0"
            assert found[ids[1]].text == "sample 1"
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM passage_translation WHERE translator_name = 'test-fetch-many'"
                )
            conn.commit()

    def test_human_translation_wins_over_machine(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM passage LIMIT 1")
            row = cur.fetchone()
        if row is None:
            pytest.skip("corpus not seeded")
        pid = str(row["id"])

        from tafahhum.language.translate import store

        try:
            store(conn, pid, Translation(
                "machine version", Language.EN, "MACHINE", "test-machine", "m",
                VerificationStatus.MACHINE_PROPOSED,
            ))
            store(conn, pid, Translation(
                "human version", Language.EN, "HUMAN", "test-human", None,
                VerificationStatus.VERIFIED,
            ))
            found = fetch_many(conn, [pid], Language.EN)
            assert found[pid].text == "human version"
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM passage_translation "
                    "WHERE translator_name IN ('test-machine', 'test-human')"
                )
            conn.commit()
