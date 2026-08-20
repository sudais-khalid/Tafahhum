"""The work catalogue and its classification provenance.

The property under test is that a school label is never asserted without a named
source. A filter for "Sunni works" must mean "works a stated reference places
under a Sunni heading" — not Tafahhum's own judgement, which it has no standing
to make.
"""

from __future__ import annotations

import psycopg
import pytest

from tafahhum.core.config import get_settings
from tafahhum.corpus.catalogue import (
    CATALOGUE,
    CLASSIFICATION_SOURCE,
    COMMENTARY_METHODS,
    SUNNI_TRADITIONS,
    commentaries,
    default_selection,
    sunni_works,
    unclassified_works,
)


@pytest.fixture(scope="module")
def conn():
    """One connection shared by every database test in this module."""
    try:
        c = psycopg.connect(get_settings().dsn, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError as exc:
        pytest.skip(f"database unavailable: {exc}")
    with c:
        yield c


VALID_TRADITIONS = {
    "SUNNI", "SUNNI_SUFI", "SUNNI_SALAFI", "TWELVER_SHIA", "ZAYDI_SHIA",
    "MUTAZILA", "IBADI", "MODERNIST", "EARLY", "UNCLASSIFIED",
}
VALID_METHODS = {
    "BI_AL_MATHUR", "BI_AL_RAY", "FIQHI", "LUGHAWI", "BALAGHI", "SUFI_ISHARI",
    "KALAMI", "QIRAAT", "GHARIB", "MIXED", "UNCLASSIFIED",
}


class TestCatalogueShape:
    def test_slugs_are_unique(self):
        slugs = [e.slug for e in CATALOGUE]
        assert len(slugs) == len(set(slugs))

    def test_source_slugs_are_unique(self):
        source = [e.source_slug for e in CATALOGUE]
        assert len(source) == len(set(source))

    def test_every_entry_has_both_scripts(self):
        for e in CATALOGUE:
            assert e.title_ar and e.title_en
            assert e.author_ar and e.author_en

    def test_traditions_are_valid(self):
        assert {e.tradition for e in CATALOGUE} <= VALID_TRADITIONS

    def test_methods_are_valid(self):
        assert {e.method for e in CATALOGUE} <= VALID_METHODS

    def test_default_selection_is_not_empty(self):
        assert len(default_selection()) >= 5

    def test_default_selection_spans_methods(self):
        """A default that is all one method would bias every first query."""
        assert len({e.method for e in default_selection()}) >= 3


class TestClassificationHonesty:
    def test_unclassified_entries_explain_themselves(self):
        """An unclassified work must say why, not just be blank."""
        for e in unclassified_works():
            assert e.note, f"{e.slug} is UNCLASSIFIED with no explanation"

    def test_kashshaf_is_not_counted_as_sunni(self):
        """The reference places al-Kashshaf under Mu'tazila.

        It was ingested as Sunni before the catalogue existed; this pins the
        correction so a Sunni-only selection cannot silently include it.
        """
        entry = next(e for e in CATALOGUE if e.slug == "zamakhshari-al-kashshaf")
        assert entry.tradition == "MUTAZILA"
        assert entry not in sunni_works()
        assert entry.note and "Mu'tazila" in entry.note

    def test_tanwir_al_miqbas_attribution_is_flagged(self):
        entry = next(e for e in CATALOGUE if e.slug == "tanwir-al-miqbas")
        assert entry.tradition == "EARLY"
        assert entry.note and "disputed" in entry.note.lower()

    def test_death_years_are_sparse_not_invented(self):
        """Most works have no death year yet, and that is the honest state."""
        with_years = [e for e in CATALOGUE if e.death_hijri is not None]
        assert len(with_years) < len(CATALOGUE), "every work has a date; suspicious"
        for e in with_years:
            assert 1 <= e.death_hijri <= 1500

    def test_sunni_traditions_are_the_reference_headings(self):
        assert set(SUNNI_TRADITIONS) == {"SUNNI", "SUNNI_SUFI", "SUNNI_SALAFI"}


class TestGrouping:
    def test_commentaries_exclude_apparatus(self):
        """Grammar and qira'at works answer a different question."""
        slugs = {e.slug for e in commentaries()}
        assert not any("irab" in s for s in slugs)
        assert not any("qiraat" in s or "nashr" in s for s in slugs)

    def test_commentary_methods_exclude_linguistic_only(self):
        assert "LUGHAWI" not in COMMENTARY_METHODS
        assert "QIRAAT" not in COMMENTARY_METHODS
        assert "BI_AL_MATHUR" in COMMENTARY_METHODS

    def test_sunni_and_unclassified_do_not_overlap(self):
        assert not ({e.slug for e in sunni_works()} & {e.slug for e in unclassified_works()})


@pytest.mark.db
class TestCatalogueInDatabase:
    def test_no_classified_work_lacks_a_source(self, conn):
        """The database constraint, checked against real data."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) AS n FROM tafsir_work "
                "WHERE tradition <> 'UNCLASSIFIED' AND classification_source IS NULL"
            )
            assert cur.fetchone()["n"] == 0

    def test_classification_source_is_recorded(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT classification_source FROM tafsir_work "
                "WHERE classification_source IS NOT NULL"
            )
            sources = {r["classification_source"] for r in cur.fetchall()}
        if sources:
            assert sources == {CLASSIFICATION_SOURCE}

    def test_classification_is_unverified(self, conn):
        """A tertiary reference is a source, not a scholarly authority."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) AS n FROM tafsir_work "
                "WHERE tradition <> 'UNCLASSIFIED' "
                "AND classification_status <> 'UNVERIFIED'"
            )
            assert cur.fetchone()["n"] == 0

    def test_unsourced_classification_is_rejected(self, conn):
        with conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                    INSERT INTO tafsir_work (slug, title_ar, tradition)
                    VALUES ('t-bad-class', 'x', 'SUNNI')
                    """
            )
        conn.rollback()

    def test_kashshaf_stored_as_mutazila(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tradition::text AS tradition FROM tafsir_work "
                "WHERE slug = 'zamakhshari-al-kashshaf'"
            )
            row = cur.fetchone()
        if row is None:
            pytest.skip("catalogue not ingested")
        assert row["tradition"] == "MUTAZILA"
