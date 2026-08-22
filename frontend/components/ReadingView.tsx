"use client";

import { useState } from "react";
import { COPY } from "@/lib/i18n";
import { SummaryPanel } from "./SummaryPanel";
import type { Reading, ReadingNote, UiLanguage } from "@/lib/types";

/* Reading an ayah, clause by clause.
 *
 * The evidence view answers "show me the sources". This answers "help me
 * understand this ayah", which is a different question and wants a different
 * shape: the ayah, then each clause of it, then what commentators said about
 * that clause, in the reader's language where a translation exists.
 *
 * Transparency is kept by showing how each attachment was established rather
 * than by hiding the machinery: a passage that quoted the clause is marked
 * differently from one matched by word overlap, because the second is a weaker
 * claim and a reader deserves to know which they are looking at. */

function Note({ note, language }: { note: ReadingNote; language: UiLanguage }) {
  const t = COPY[language];
  const [expanded, setExpanded] = useState(false);
  const inferred = note.alignment_basis === "OVERLAP";

  return (
    <article className="note">
      <header className="note-head">
        <span className="note-author">{note.author}</span>
        {note.death_year_hijri && (
          <span className="note-date">
            {t.died} {note.death_year_hijri} AH
          </span>
        )}
        <span className="note-ref">[{note.reference_number}]</span>
      </header>

      {/* The reader's language first when a translation exists — this view is
          for understanding. The Arabic stays one click away, never replaced. */}
      {note.translation ? (
        <p className="note-translation" lang={language} dir={language === "en" ? "ltr" : "rtl"}>
          {note.translation}
        </p>
      ) : (
        <p className="note-gist" lang="ar" dir="rtl">
          {note.gist ?? note.text.slice(0, 220)}
        </p>
      )}

      <div className="note-actions">
        <button type="button" onClick={() => setExpanded(!expanded)}>
          {expanded ? t.hideArabic : t.showArabic}
        </button>
        {inferred && (
          <span className="chip" data-tone="warn">
            {t.matchedByOverlap}
          </span>
        )}
        {note.is_machine_translation && (
          <span className="chip" data-tone="warn">
            {t.machineTranslation}
          </span>
        )}
      </div>

      {expanded && (
        <div className="note-full reveal">
          <p className="note-arabic" lang="ar" dir="rtl">
            {note.text}
          </p>
          <p className="note-citation">{note.citation}</p>
          {note.translator_name && (
            <p className="note-citation">
              {t.translationInto(t.languageName)} · {note.translator_name}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

export function ReadingView({
  reading,
  language,
  works,
}: {
  reading: Reading;
  language: UiLanguage;
  works?: string[] | null;
}) {
  const t = COPY[language];

  return (
    <div className="reading">
      <header className="reading-head">
        <h2 className="reading-title">
          {reading.surah_name_en} {reading.reference}
        </h2>
        <span className="reading-counts">
          {t.readingCounts(reading.counts.clauses, reading.counts.works)}
        </span>
      </header>

      {/* The whole ayah first, so a reader sees it before it is taken apart. */}
      <section className="ayah reveal">
        <div className="ayah-label">{t.ayahHeading}</div>
        <p className="ayah-text" lang="ar" dir="rtl">
          {reading.text_uthmani}
        </p>
        {reading.translations.slice(0, 1).map((tr) => (
          <div className="ayah-translation" key={tr.translation_slug}>
            <p lang={language} dir={language === "en" ? "ltr" : "rtl"}>
              {tr.text}
            </p>
            <span className="ayah-translator">{tr.translator_name}</span>
          </div>
        ))}
      </section>

      <SummaryPanel
        surah={reading.surah_number}
        ayah={reading.ayah_number}
        language={language}
        works={works}
      />

      <p className="method-note">{reading.method_note}</p>

      <ol className="clauses">
        {reading.phrases.map((phrase, i) => (
          <li className="clause reveal" key={phrase.index}>
            <div className="clause-head">
              <span className="clause-number">{i + 1}</span>
              <p className="clause-text" lang="ar" dir="rtl">
                {phrase.text_ar}
              </p>
            </div>

            {phrase.notes.length > 0 ? (
              <>
                <div className="clause-meta">
                  {t.scholarsOnThisClause(phrase.scholar_count)}
                </div>
                <div className="clause-notes">
                  {phrase.notes.map((n) => (
                    <Note key={n.passage_id} note={n} language={language} />
                  ))}
                </div>
              </>
            ) : (
              <div className="clause-meta">{t.noSeparateTreatment}</div>
            )}
          </li>
        ))}
      </ol>

      {reading.further_discussion.count > 0 && (
        <section className="further">
          <div className="section-head">
            <h2>{t.furtherDiscussion}</h2>
            <span className="count">{reading.further_discussion.count}</span>
          </div>
          <p className="method-note">{reading.further_discussion.explanation}</p>
          <div className="clause-notes">
            {reading.further_discussion.notes.map((n) => (
              <Note key={n.passage_id} note={n} language={language} />
            ))}
          </div>
        </section>
      )}

      <section className="references">
        <div className="section-head">
          <h2>{t.referencesHeading}</h2>
          <span className="count">{t.sourcesConsulted(reading.references.length)}</span>
        </div>
        <ol className="ref-list">
          {reading.references.map((r) => (
            <li className="ref-item" key={r.work_slug}>
              <span className="ref-number">[{r.number}]</span>
              <div className="ref-body">
                <div className="ref-title">{r.citation}</div>
                <div className="ref-title-ar" lang="ar" dir="rtl">
                  {r.author_ar} — {r.work_title_ar}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
