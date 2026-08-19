"""Database-backed tests.

Require a running PostgreSQL with migrations applied and the seed corpus ingested:

    docker compose up -d db
    uv run python -m tafahhum.db.migrate
    python ../scripts/fetch_corpus.py
"""

from __future__ import annotations

import psycopg
import pytest

from tafahhum.core.config import get_settings
from tafahhum.core.enums import EvidenceType, Language, QueryType
from tafahhum.pipeline import QueryRequest, run_query
from tafahhum.quran.reference import AyahRef
from tafahhum.retrieval.search import search_sparse, search_structural

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def conn():
    settings = get_settings()
    try:
        connection = psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError as exc:
        pytest.skip(f"database unavailable: {exc}")
    with connection:
        yield connection


@pytest.fixture(scope="module")
def seeded(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM published_passage")
        if cur.fetchone()["n"] == 0:
            pytest.skip("corpus not seeded; run scripts/fetch_corpus.py")
    return True


class TestSchemaIntegrity:
    def test_raw_text_is_immutable(self, conn, seeded):
        """The trigger must reject an edit to raw_text, not silently accept it."""
        with conn.cursor() as cur:
            cur.execute("SELECT id, raw_text FROM passage LIMIT 1")
            row = cur.fetchone()
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "UPDATE passage SET raw_text = %s WHERE id = %s",
                    ("tampered", row["id"]),
                )
        conn.rollback()

    def test_verified_text_is_writable(self, conn, seeded):
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM passage LIMIT 1")
            pid = cur.fetchone()["id"]
            cur.execute(
                "UPDATE passage SET verified_text = %s WHERE id = %s",
                ("corrected reading", pid),
            )
        conn.rollback()

    def test_scholarly_rule_requires_a_reference(self, conn):
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    """
                    INSERT INTO scholarly_rule
                        (rule_key, name, description, tier, source_book)
                    VALUES ('t_bad', 'x', 'y', 'SCHOLARLY_METHOD', 'Some Book')
                    """
                )
        conn.rollback()

    def test_structural_rule_may_not_claim_a_book(self, conn):
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    """
                    INSERT INTO scholarly_rule
                        (rule_key, name, description, tier, source_book, source_reference)
                    VALUES ('t_bad2', 'x', 'y', 'QUERY_STRATEGY', 'Some Book', '1/1')
                    """
                )
        conn.rollback()

    def test_verified_requires_a_reviewer(self, conn):
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    """
                    UPDATE scholarly_rule SET verification_status = 'VERIFIED'
                    WHERE rule_key = 'strategy.hybrid_retrieval'
                    """
                )
        conn.rollback()

    def test_no_rule_claims_a_scholarly_source_yet(self, conn):
        """Guards the SOURCE_POLICY §6 commitment.

        If this ever fails, a scholarly rule was added — which is fine, but it
        must have gone through human verification. Update this test deliberately.
        """
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) AS n FROM scholarly_rule "
                "WHERE source_book <> 'TAFAHHUM_BASELINE'"
            )
            assert cur.fetchone()["n"] == 0


class TestRetrieval:
    def test_structural_finds_the_ayah(self, conn, seeded):
        results = search_structural(conn, [AyahRef(2, 255, 255)])
        assert results
        assert all(p.surah_number == 2 for p in results)

    def test_structural_covers_many_works(self, conn, seeded):
        """Retrieval must not be monopolised by the longest commentary."""
        results = search_structural(conn, [AyahRef(2, 255, 255)], per_work_limit=3)
        assert len({p.citation.work_slug for p in results}) >= 5

    def test_per_work_cap_is_honoured(self, conn, seeded):
        results = search_structural(conn, [AyahRef(2, 255, 255)], per_work_limit=2)
        counts: dict[str, int] = {}
        for p in results:
            counts[p.citation.work_slug] = counts.get(p.citation.work_slug, 0) + 1
        assert max(counts.values()) <= 2

    def test_range_overlap(self, conn, seeded):
        """A query for 2:256 finds passages aligned to a range containing it."""
        assert search_structural(conn, [AyahRef(2, 254, 258)])

    def test_sparse_requires_normalised_query(self, conn, seeded):
        """Alef maqsura in the query must still match the normalised index."""
        assert search_sparse(conn, "معنى", limit=5)

    def test_sparse_finds_arabic_phrase(self, conn, seeded):
        assert search_sparse(conn, "الحي القيوم", limit=5)

    def test_work_filter(self, conn, seeded):
        results = search_structural(
            conn, [AyahRef(2, 255, 255)], work_slugs=["tabari-jami-al-bayan"]
        )
        assert results
        assert {p.citation.work_slug for p in results} == {"tabari-jami-al-bayan"}


class TestPipeline:
    def test_english_ayah_query(self, conn, seeded):
        pkg = run_query(
            conn,
            QueryRequest(text="What do the Tafasir say about 2:255?", user_language=Language.EN),
        )
        assert pkg.query_type is QueryType.AYAH_TAFSIR
        assert [str(r) for r in pkg.refs] == ["2:255"]
        assert pkg.passage_count > 0
        assert len(pkg.works) >= 5

    def test_quranic_text_is_carried_separately(self, conn, seeded):
        """The ayah must never arrive mixed into the commentary."""
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.EN))
        assert pkg.ayah_texts
        assert pkg.ayah_texts[0].evidence_kind is EvidenceType.QURANIC_TEXT
        assert all(
            p.evidence_kind is not EvidenceType.QURANIC_TEXT
            for w in pkg.works for p in w.passages
        )

    def test_urdu_query_retrieves_arabic_sources(self, conn, seeded):
        pkg = run_query(
            conn,
            QueryRequest(text="آیت الکرسی کی تفسیر کیا ہے؟", user_language=Language.UR),
        )
        assert [str(r) for r in pkg.refs] == ["2:255"]
        assert pkg.passage_count > 0

    def test_arabic_query(self, conn, seeded):
        pkg = run_query(
            conn,
            QueryRequest(text="ما تفسير قوله تعالى الحي القيوم", user_language=Language.AR),
        )
        assert pkg.passage_count > 0

    def test_comparative_isolates_named_works(self, conn, seeded):
        pkg = run_query(
            conn,
            QueryRequest(text="Compare Tabari and Qurtubi on 2:255", user_language=Language.EN),
        )
        assert pkg.query_type is QueryType.COMPARATIVE
        assert {w.work_slug for w in pkg.works} == {
            "tabari-jami-al-bayan", "qurtubi-al-jami-li-ahkam"
        }

    def test_every_passage_carries_a_citation(self, conn, seeded):
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.EN))
        for w in pkg.works:
            for p in w.passages:
                assert p.citation.work_slug and p.citation.edition_slug
                assert p.citation.passage_id == p.passage_id

    def test_missing_page_citation_is_disclosed(self, conn, seeded):
        """The seeded editions have no print provenance; that must be stated."""
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.EN))
        assert pkg.page_level_citation_coverage == 0.0
        assert any("page-level citation" in n for n in pkg.notes)

    def test_empty_evidence_is_reported_not_invented(self, conn, seeded):
        """An unindexed ayah must yield an explicit statement, not a guess."""
        pkg = run_query(conn, QueryRequest(text="Surah 50 ayah 20", user_language=Language.EN))
        assert pkg.is_empty
        assert any("Insufficient verified evidence" in n for n in pkg.notes)

    def test_rules_are_recorded(self, conn, seeded):
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.EN))
        assert pkg.rules_applied
        assert all(r["provenance"] for r in pkg.rules_applied)

    def test_citable_ids_are_exactly_the_retrieved_passages(self, conn, seeded):
        """The generation layer may cite these and nothing else."""
        pkg = run_query(conn, QueryRequest(text="2:255", user_language=Language.EN))
        ids = {p.passage_id for w in pkg.works for p in w.passages}
        assert pkg.citable_passage_ids == ids
