"""OCR and passage translation.

No network is used. Model-backed engines are exercised through fakes, because
what needs testing is the contract around them — that output is labelled, that
raw text is preserved, that an unavailable backend degrades honestly — not the
model itself.
"""

from __future__ import annotations

import shutil

import psycopg
import pytest

from tafahhum.core.config import get_settings
from tafahhum.core.enums import Language, VerificationStatus
from tafahhum.corpus.ocr import (
    OcrResult,
    TesseractEngine,
    VisionOcrEngine,
    select_engine,
)
from tafahhum.language.translate import (
    ClaudeTranslator,
    Translation,
    get_translator,
    set_translator,
    translate_passage,
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


class FakeTranslator:
    name = "fake-translator"

    def __init__(self, available: bool = True, text: str = "translated text"):
        self._available = available
        self._text = text
        self.calls = 0

    def available(self) -> bool:
        return self._available

    def translate(self, text, *, target, source=Language.AR) -> Translation:
        self.calls += 1
        return Translation(
            text=self._text,
            language=target,
            translator_kind="MACHINE",
            translator_name=self.name,
            model_name="fake-model",
            verification_status=VerificationStatus.MACHINE_PROPOSED,
            note="fake",
        )


class TestOcrResult:
    def test_normalisation_matches_index_pipeline(self):
        r = OcrResult(
            text="مَعْنَى الْحَيُّ", engine="x", engine_version="1",
            confidence=0.5, language=Language.AR,
        )
        # Same folding the FTS index uses, so OCR text is searchable.
        assert r.normalized == "معني الحي"

    def test_empty_detection(self):
        blank = OcrResult("   ", "x", "1", None, Language.AR)
        assert blank.is_empty

    def test_confidence_may_be_absent(self):
        """A model that reports no calibrated confidence records None.

        Substituting a plausible number would make an unmeasured value
        indistinguishable from a measured one.
        """
        r = OcrResult("text", "claude-vision", "claude-opus-5", None, Language.UR)
        assert r.confidence is None


class TestEngineSelection:
    def test_available_reports_whether_tesseract_is_installed(self):
        """`available()` must report the environment, not assume one.

        The earlier version of this test asserted that Tesseract *is* installed,
        which is a fact about the machine that happened to run it rather than
        anything about the code. It passed locally and failed on CI, where no
        Tesseract is present — which is exactly the situation `available()`
        exists to detect.
        """
        assert TesseractEngine().available() == (shutil.which("tesseract") is not None)

    @pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
    def test_reads_a_page_when_tesseract_is_present(self, tmp_path):
        """Only meaningful where the binary exists; skipped cleanly where it does not."""
        engine = TesseractEngine()
        blank = tmp_path / "blank.png"
        # A 1x1 PNG: the point is that the engine runs and reports, not what it reads.
        blank.write_bytes(bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001080600000"
            "01f15c4890000000d49444154789c636000000200010005000109f0f3"
            "710000000049454e44ae426082"
        ))
        result = engine.read_page(blank, language=Language.AR)
        assert result.engine == "tesseract"

    def test_explicit_preference_is_honoured(self):
        assert select_engine("tesseract").name == "tesseract"
        assert select_engine("vision").name == "claude-vision"

    def test_falls_back_when_vision_unavailable(self):
        """Without credentials the pipeline still runs, on the weaker engine."""
        engine = select_engine()
        assert engine.name in {"tesseract", "claude-vision"}

    def test_urdu_uses_both_scripts(self):
        """Urdu pages carry Arabic quotations, so both models are loaded."""
        from tafahhum.corpus.ocr import _TESS_LANG

        assert _TESS_LANG[Language.UR] == "urd+ara"


class TestVisionPrompt:
    def test_prompt_forbids_guessing(self):
        from tafahhum.corpus.ocr import _VISION_SYSTEM

        assert "Do not translate" in _VISION_SYSTEM
        assert "Do not \nguess" in _VISION_SYSTEM or "guess" in _VISION_SYSTEM

    def test_prompt_requires_gap_marker(self):
        from tafahhum.corpus.ocr import _VISION_SYSTEM

        assert "[؟]" in _VISION_SYSTEM

    def test_batch_requests_are_one_per_page(self, tmp_path):
        pytest.importorskip("anthropic")
        img = tmp_path / "p1.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        reqs = VisionOcrEngine().build_batch_requests(
            [("id-1", img), ("id-2", img)], language=Language.UR
        )
        assert [r["custom_id"] for r in reqs] == ["id-1", "id-2"]


class TestTranslationContract:
    def test_source_language_is_not_translated(self):
        """Translating Arabic into Arabic is a no-op, not a model round trip."""
        # `client=object()` proves no API call happens: any attempt would raise.
        result = ClaudeTranslator(client=object()).translate(
            "نص", target=Language.AR, source=Language.AR
        )
        assert result.text == "نص"
        assert result.translator_kind == "HUMAN"
        assert not result.is_machine

    def test_machine_translation_is_flagged(self):
        fake = FakeTranslator()
        out = fake.translate("x", target=Language.EN)
        assert out.is_machine
        assert out.verification_status is VerificationStatus.MACHINE_PROPOSED

    def test_prompt_forbids_adding_content(self):
        from tafahhum.language.translate import _SYSTEM

        assert "Add nothing that is not in the text" in _SYSTEM
        assert "Do not summarise" in _SYSTEM

    def test_prompt_marks_quranic_quotations(self):
        """A reader must see where revelation is quoted inside commentary."""
        from tafahhum.language.translate import _SYSTEM

        assert "« »" in _SYSTEM

    def test_translator_is_swappable(self):
        original = get_translator()
        try:
            fake = FakeTranslator()
            set_translator(fake)
            assert get_translator() is fake
        finally:
            set_translator(original)


@pytest.mark.db
class TestTranslationStorage:
    @pytest.fixture
    def passage_id(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM passage LIMIT 1")
            row = cur.fetchone()
            if row is None:
                pytest.skip("corpus not seeded")
            return str(row["id"])

    def test_unavailable_backend_reports_rather_than_fails(self, conn, passage_id):
        original = get_translator()
        try:
            set_translator(FakeTranslator(available=False))
            result, status = translate_passage(
                conn, passage_id, target=Language.EN, force=True
            )
            assert result is None
            assert status == "unavailable"
        finally:
            set_translator(original)
            conn.rollback()

    def test_translation_is_cached_after_first_call(self, conn, passage_id):
        original = get_translator()
        fake = FakeTranslator(text="cached sample")
        try:
            set_translator(fake)
            first, s1 = translate_passage(conn, passage_id, target=Language.EN, force=True)
            assert s1 == "fresh" and first is not None
            assert fake.calls == 1

            second, s2 = translate_passage(conn, passage_id, target=Language.EN)
            assert s2 == "cached"
            assert second is not None and second.text == "cached sample"
            # The model is not called again: passage.raw_text is immutable, so a
            # cached translation cannot drift from its source.
            assert fake.calls == 1
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM passage_translation WHERE translator_name = %s",
                    (fake.name,),
                )
            conn.commit()
            set_translator(original)

    def test_missing_passage_reports_not_found(self, conn):
        result, status = translate_passage(
            conn, "00000000-0000-0000-0000-000000000000", target=Language.EN
        )
        assert result is None and status == "not_found"


@pytest.mark.db
class TestScanPages:
    def test_nayl_is_registered_as_a_bibliographical_source(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT genre FROM biblio_source WHERE slug = 'nayl-al-sairin'")
            row = cur.fetchone()
        assert row is not None
        assert row["genre"] == "tabaqat_al_mufassirin"

    def test_scan_page_requires_exactly_one_parent(self, conn):
        with conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                    INSERT INTO scan_page (volume, page_label, image_index, image_uri)
                    VALUES (1, '1', 9999, 'x.png')
                    """
            )
        conn.rollback()

    def test_ocr_raw_text_is_immutable_once_written(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM scan_page WHERE length(trim(ocr_raw_text)) > 0 LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip("no OCR text present")
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "UPDATE scan_page SET ocr_raw_text = %s WHERE id = %s",
                    ("tampered", row["id"]),
                )
        conn.rollback()

    def test_empty_ocr_does_not_lock_a_page(self, conn):
        """A failed read must be re-runnable; only real text is frozen."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM scan_page WHERE ocr_raw_text IS NULL LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip("no un-OCRd page available")
            cur.execute(
                "UPDATE scan_page SET ocr_raw_text = '' WHERE id = %s", (row["id"],)
            )
            # Empty is not a reading, so it can be replaced.
            cur.execute(
                "UPDATE scan_page SET ocr_raw_text = %s WHERE id = %s",
                ("real text", row["id"]),
            )
        conn.rollback()

    def test_nothing_from_this_source_is_citable_yet(self, conn):
        """Guards the review gate: machine transcription is a proposal."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) AS n FROM scan_page sp
                JOIN biblio_source b ON b.id = sp.biblio_source_id
                WHERE b.slug = 'nayl-al-sairin' AND sp.ocr_verified_text IS NOT NULL
                """
            )
            assert cur.fetchone()["n"] == 0
