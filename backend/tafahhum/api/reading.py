"""The reading view.

A different shape of answer from `/query`. `/query` returns evidence for an
audit; this returns an ayah organised for reading: clause by clause, with what
each commentator said about each clause, in the reader's language where a
translation exists.

Two rules shape it.

Nothing is dropped. Passages that align to no clause — discussions of the ayah's
virtues, its occasion of revelation, a hadith reported under it — are collected
into their own group rather than filtered out. A reading view that silently
omitted evidence would be worse than the raw list it replaces.

Nothing is generated. Every line shown is either the ayah, a stored translation,
or text extracted verbatim from a passage. There is no summary written here,
because a summary of exegesis is exegesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg

from tafahhum.core.enums import Language
from tafahhum.language.translate import fetch_many


@dataclass
class ScholarNote:
    """One commentator's passage under a clause."""

    passage_id: str
    work_slug: str
    work_title_ar: str
    work_title_en: str | None
    author_ar: str
    author_en: str | None
    death_year_hijri: int | None
    tradition: str
    gist: str | None
    text: str
    translation: str | None
    translator_name: str | None
    is_machine_translation: bool
    basis: str
    confidence: float
    citation: str
    resolves_to_page: bool


@dataclass
class PhraseGroup:
    index: int
    text_ar: str
    support: int
    notes: list[ScholarNote] = field(default_factory=list)

    @property
    def scholar_count(self) -> int:
        return len({n.work_slug for n in self.notes})


def _citation(row: dict, language: str) -> str:
    author = row["author_en"] if language != "ar" and row["author_en"] else row["author_ar"]
    title = (
        row["work_title_en"]
        if language != "ar" and row["work_title_en"]
        else row["work_title_ar"]
    )
    parts = [f"{author}, {title}"]
    if row["volume"] is not None:
        parts.append(f"vol. {row['volume']}")
    if row["page_start"] is not None:
        parts.append(f"p. {row['page_start']}")
    else:
        parts.append("[no page-level citation available for this edition]")
    return ", ".join(parts)


_PASSAGE_SQL = """
    SELECT p.id AS passage_id,
           COALESCE(p.verified_text, p.raw_text) AS text,
           p.volume, p.page_start, p.sequence_index,
           pp.basis::text AS basis, pp.confidence, pp.gist,
           pp.opens_discussion,
           ph.phrase_index,
           w.slug AS work_slug, w.title_ar AS work_title_ar, w.title_en AS work_title_en,
           w.tradition::text AS tradition, w.catalogue_rank,
           m.name_ar AS author_ar, m.name_en AS author_en, m.death_year_hijri
    FROM published_passage p
    JOIN passage_ayah pa ON pa.passage_id = p.id
    JOIN tafsir_work w ON w.id = p.tafsir_work_id
    LEFT JOIN mufassir m ON m.id = p.author_id
    LEFT JOIN passage_phrase pp ON pp.passage_id = p.id
    LEFT JOIN ayah_phrase ph ON ph.id = pp.phrase_id
    WHERE pa.surah_number = %s AND pa.ayah_start = %s
      AND (%s::text[] IS NULL OR w.slug = ANY(%s::text[]))
"""


def build_reading(
    conn: psycopg.Connection,
    *,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None = None,
    per_phrase_per_work: int = 1,
) -> dict:
    """Assemble the clause-by-clause reading of one ayah."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.text_uthmani, s.name_ar, s.name_en_translit, s.ayah_count
            FROM ayah a
            JOIN surah s ON s.number = a.surah_number
            JOIN quran_text_source q ON q.id = a.text_source_id
            WHERE q.is_default AND a.surah_number = %s AND a.ayah_number = %s
            """,
            (surah, ayah),
        )
        ayah_row = cur.fetchone()
        if ayah_row is None:
            return {}

        translations: list[dict] = []
        if language is not Language.AR:
            cur.execute(
                """
                SELECT text, translator_name, translation_slug
                FROM ayah_translation
                WHERE language = %s AND surah_number = %s AND ayah_number = %s
                ORDER BY translation_slug
                """,
                (language.value, surah, ayah),
            )
            translations = cur.fetchall()

        cur.execute(
            "SELECT phrase_index, text_ar, support FROM ayah_phrase "
            "WHERE surah_number = %s AND ayah_number = %s ORDER BY phrase_index",
            (surah, ayah),
        )
        phrase_rows = cur.fetchall()

        cur.execute(_PASSAGE_SQL, (surah, ayah, work_slugs, work_slugs))
        rows = cur.fetchall()

    passage_translations = (
        fetch_many(conn, [str(r["passage_id"]) for r in rows], language)
        if language is not Language.AR
        else {}
    )

    def to_note(row: dict) -> ScholarNote:
        stored = passage_translations.get(str(row["passage_id"]))
        return ScholarNote(
            passage_id=str(row["passage_id"]),
            work_slug=row["work_slug"],
            work_title_ar=row["work_title_ar"],
            work_title_en=row["work_title_en"],
            author_ar=row["author_ar"] or "—",
            author_en=row["author_en"],
            death_year_hijri=row["death_year_hijri"],
            tradition=row["tradition"],
            gist=row["gist"],
            text=row["text"],
            translation=stored.text if stored and stored.text else None,
            translator_name=stored.translator_name if stored else None,
            is_machine_translation=bool(stored and stored.is_machine),
            basis=(row["basis"] or "UNALIGNED"),
            confidence=float(row["confidence"] or 0.0),
            citation=_citation(row, language.value),
            resolves_to_page=row["page_start"] is not None,
        )

    groups = {
        r["phrase_index"]: PhraseGroup(
            index=r["phrase_index"], text_ar=r["text_ar"], support=r["support"]
        )
        for r in phrase_rows
    }
    unaligned: list[ScholarNote] = []

    # Within a work, take where it *begins* treating the clause, not whichever
    # chunk scored highest.
    #
    # A long commentary contributes many chunks to one clause, and the
    # high-confidence ones are often continuations — an isnad tail, a line of
    # cited poetry, a digression. Those are unreadable on their own. A chunk
    # that brackets the clause is a discussion opening, and among openings the
    # earliest in reading order is the one that starts the argument.
    rows.sort(
        key=lambda r: (
            r["catalogue_rank"],
            r["work_slug"],
            0 if r["opens_discussion"] else 1,
            0 if r["basis"] == "QUOTED" else 1,
            r["sequence_index"],
        )
    )

    per_work_seen: dict[tuple[int | None, str], int] = {}
    for row in rows:
        key = (row["phrase_index"], row["work_slug"])
        seen = per_work_seen.get(key, 0)
        if seen >= per_phrase_per_work:
            continue
        per_work_seen[key] = seen + 1

        # A continuation shown as a commentator's treatment of a clause reads
        # as a fragment and misrepresents what they said. Continuations stay in
        # the corpus and remain retrievable; they just do not lead a clause.
        if row["phrase_index"] is not None and not row["opens_discussion"]:
            continue

        note = to_note(row)
        if row["phrase_index"] is None or row["phrase_index"] not in groups:
            unaligned.append(note)
        else:
            groups[row["phrase_index"]].notes.append(note)

    ordered = [groups[i] for i in sorted(groups)]

    # Fold a clause nobody treated separately into its neighbour.
    #
    # The segmentation splits wherever spans are attested, but commentators
    # often handle two clauses together — "لا تأخذه سنة ولا نوم" is discussed as
    # one thought, so the second half attracts no opening of its own. Showing it
    # as an empty heading suggests the tradition passed over it in silence,
    # which is false. The words stay visible, joined to the clause they were
    # actually discussed under.
    merged: list[PhraseGroup] = []
    for group in ordered:
        if not group.notes and merged:
            previous = merged[-1]
            merged[-1] = PhraseGroup(
                index=previous.index,
                text_ar=f"{previous.text_ar} {group.text_ar}".strip(),
                support=max(previous.support, group.support),
                notes=previous.notes,
            )
        else:
            merged.append(group)

    # A leading clause with no notes has no predecessor to join, so it folds
    # forward into the one after it instead.
    while len(merged) > 1 and not merged[0].notes:
        head, nxt = merged[0], merged[1]
        merged[1] = PhraseGroup(
            index=head.index,
            text_ar=f"{head.text_ar} {nxt.text_ar}".strip(),
            support=max(head.support, nxt.support),
            notes=nxt.notes,
        )
        merged.pop(0)

    ordered = merged

    # Numbered reference list, in the order works first appear in the reading.
    references: list[dict] = []
    seen_works: dict[str, int] = {}
    for note in [n for g in ordered for n in g.notes] + unaligned:
        if note.work_slug in seen_works:
            continue
        seen_works[note.work_slug] = len(references) + 1
        references.append(
            {
                "number": len(references) + 1,
                "work_slug": note.work_slug,
                "work_title_ar": note.work_title_ar,
                "work_title_en": note.work_title_en,
                "author_ar": note.author_ar,
                "author_en": note.author_en,
                "death_year_hijri": note.death_year_hijri,
                "tradition": note.tradition,
                "citation": note.citation,
                "resolves_to_page": note.resolves_to_page,
            }
        )

    def serialise_note(n: ScholarNote) -> dict:
        return {
            "passage_id": n.passage_id,
            "reference_number": seen_works.get(n.work_slug, 0),
            "work_slug": n.work_slug,
            "author": n.author_en if language is not Language.AR and n.author_en else n.author_ar,
            "author_ar": n.author_ar,
            "death_year_hijri": n.death_year_hijri,
            "tradition": n.tradition,
            "gist": n.gist,
            "text": n.text,
            "translation": n.translation,
            "translator_name": n.translator_name,
            "is_machine_translation": n.is_machine_translation,
            "alignment_basis": n.basis,
            "alignment_confidence": round(n.confidence, 3),
            "citation": n.citation,
        }

    total_notes = sum(len(g.notes) for g in ordered) + len(unaligned)

    return {
        "surah_number": surah,
        "ayah_number": ayah,
        "reference": f"{surah}:{ayah}",
        "surah_name_ar": ayah_row["name_ar"],
        "surah_name_en": ayah_row["name_en_translit"],
        "surah_ayah_count": ayah_row["ayah_count"],
        "text_uthmani": ayah_row["text_uthmani"],
        "translations": translations,
        "phrases": [
            {
                "index": g.index,
                "text_ar": g.text_ar,
                "support": g.support,
                "scholar_count": g.scholar_count,
                "notes": [serialise_note(n) for n in g.notes],
            }
            for g in ordered
        ],
        "further_discussion": {
            "count": len(unaligned),
            "notes": [serialise_note(n) for n in unaligned],
            "explanation": (
                "These passages discuss the ayah without quoting a particular "
                "clause — its virtues, its occasion of revelation, or a report "
                "transmitted under it. They are shown here rather than omitted."
            ),
        },
        "references": references,
        "counts": {
            "clauses": len(ordered),
            "notes_shown": total_notes,
            "works": len(references),
        },
        "method_note": (
            "Clause boundaries are derived from the commentaries themselves: "
            "commentators bracket the clause they are treating, and the spans "
            "several of them return to are the divisions shown here. Nothing on "
            "this page is written by Tafahhum — every line is the ayah, a stored "
            "translation, or text taken verbatim from a source."
        ),
    }
