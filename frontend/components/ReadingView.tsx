"use client";

import { useState } from "react";
import { COPY } from "@/lib/i18n";
import type { Depth } from "@/lib/depth";
import { SummaryPanel } from "./SummaryPanel";
import { TranslateButton } from "./TranslateButton";
import type { Reading, ReadingNote, ReadingPhrase, UiLanguage } from "@/lib/types";

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

/** How many commentators lead a clause at learning depth. The rest are one
 *  click away and counted on the button, never dropped. */
const LEARN_VISIBLE = 2;

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

      {/* The commentator's own words, always present and never replaced. */}
      <p className="note-gist" lang="ar" dir="rtl">
        {expanded ? note.text : (note.gist ?? note.text.slice(0, 220))}
      </p>

      <div className="note-actions">
        <button type="button" onClick={() => setExpanded(!expanded)}>
          {expanded ? t.showLess : t.showFullArabic}
        </button>
        {inferred && (
          <span className="chip" data-tone="warn">
            {t.matchedByOverlap}
          </span>
        )}
      </div>

      <TranslateButton
        passageId={note.passage_id}
        language={language}
        initial={
          note.translation
            ? {
                text: note.translation,
                language,
                translator_kind: "MACHINE",
                translator_name: note.translator_name ?? "",
                model_name: null,
                verification_status: "MACHINE_PROPOSED",
                is_machine: note.is_machine_translation,
              }
            : null
        }
      />

      {expanded && (
        <div className="note-full reveal">
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

/** The notes under one clause, with the learning-depth cap made visible.
 *
 * The cap is applied here rather than in CSS on purpose. Hiding commentators
 * with a display rule would leave no honest way to say how many were held
 * back, and an interface built to show all the evidence must not quietly show
 * less of it. */
function ClauseNotes({
  notes,
  language,
  depth,
}: {
  notes: ReadingNote[];
  language: UiLanguage;
  depth: Depth;
}) {
  const t = COPY[language];
  const [showAll, setShowAll] = useState(false);
  const capped = depth === "learn" && !showAll && notes.length > LEARN_VISIBLE;
  const shown = capped ? notes.slice(0, LEARN_VISIBLE) : notes;

  return (
    <>
      <div className="clause-notes">
        {shown.map((n) => (
          <Note key={n.passage_id} note={n} language={language} />
        ))}
      </div>
      {capped && (
        <div className="clause-more">
          <button type="button" onClick={() => setShowAll(true)}>
            {t.showMoreCommentators(notes.length - LEARN_VISIBLE)}
          </button>
        </div>
      )}
    </>
  );
}

function ClauseNav({
  phrases,
  language,
}: {
  phrases: ReadingPhrase[];
  language: UiLanguage;
}) {
  const t = COPY[language];

  return (
    <div className="rail-section">
      <div className="rail-heading">{t.clausesInVerse}</div>
      <nav className="clause-nav">
        {phrases.map((phrase, i) => (
          <a
            key={phrase.index}
            href={`#clause-${phrase.index}`}
            title={t.jumpToClause(i + 1)}
          >
            <span className="clause-nav-number">{i + 1}</span>
            <span className="clause-nav-text" lang="ar" dir="rtl">
              {phrase.text_ar}
            </span>
            <span className="clause-nav-count">{phrase.scholar_count}</span>
          </a>
        ))}
      </nav>
      <p className="rail-hint">{t.clauseNavHint}</p>
    </div>
  );
}

export function ReadingView({
  reading,
  language,
  works,
  depth,
}: {
  reading: Reading;
  language: UiLanguage;
  works?: string[] | null;
  depth: Depth;
}) {
  const t = COPY[language];
  const translation = reading.translations[0];

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

      <div className="reading-layout">
        {/* The ayah stays in view while the commentary beside it scrolls. */}
        <aside className="reading-rail">
          <div className="rail-label">{t.ayahHeading}</div>
          <p className="rail-ayah" lang="ar" dir="rtl">
            {reading.text_uthmani}
          </p>

          {translation && (
            <div className="rail-translation">
              <p lang={language} dir={language === "en" ? "ltr" : "rtl"}>
                {translation.text}
              </p>
              <span className="rail-translator">{translation.translator_name}</span>
            </div>
          )}

          <ClauseNav phrases={reading.phrases} language={language} />
        </aside>

        <div className="reading-main">
          <SummaryPanel
            surah={reading.surah_number}
            ayah={reading.ayah_number}
            language={language}
            works={works}
          />

          <p className="method-note">{reading.method_note}</p>

          <ol className="clauses">
            {reading.phrases.map((phrase, i) => (
              <li
                className="clause reveal"
                key={phrase.index}
                id={`clause-${phrase.index}`}
              >
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
                    <ClauseNotes
                      notes={phrase.notes}
                      language={language}
                      depth={depth}
                    />
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
              <span className="count">
                {t.sourcesConsulted(reading.references.length)}
              </span>
            </div>
            <ol className="ref-list">
              {reading.references.map((r) => (
                <li className="ref-item" key={r.work_slug}>
                  <span className="ref-number">[{r.number}]</span>
                  <div className="ref-body">
                    <div className="ref-title">{r.citation}</div>
                    <div className="ref-title-ar" lang="ar" dir="rtl">
                      {r.author_ar}, {r.work_title_ar}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </div>
  );
}
