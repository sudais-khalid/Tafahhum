import type { Ayah, Passage, PassageTranslation, UiLanguage, Work } from "@/lib/types";
import { COPY } from "@/lib/i18n";
import { ProvenanceLadder } from "./ProvenanceLadder";
import { TranslateButton } from "./TranslateButton";

/* Quranic text is rendered by its own component, in its own colour, in its own
 * block. It is never a card in the evidence list, because it is not evidence
 * about the ayah, it is the ayah. */

export function AyahBlock({ ayah, language }: { ayah: Ayah; language: UiLanguage }) {
  const t = COPY[language];
  return (
    <section className="ayah reveal" aria-label={`${t.ayahHeading} ${ayah.reference}`}>
      <div className="ayah-label">{t.ayahHeading}</div>

      <p className="ayah-text" lang="ar" dir="rtl">
        {ayah.text_uthmani}
      </p>

      {/* Revealed text is never machine-translated. Where a rendering is shown
          it is an established translation and the translator is named. */}
      {ayah.translations.map((tr) => (
        <div className="ayah-translation" key={tr.translation_slug}>
          <p lang={tr.language} dir={tr.language === "en" ? "ltr" : "rtl"}>
            {tr.text}
          </p>
          <span className="ayah-translator">{tr.translator_name}</span>
        </div>
      ))}

      <div className="ayah-ref">
        <span lang="ar" dir="rtl">
          {ayah.surah_name_ar}
        </span>
        {"  ·  "}
        {ayah.surah_name_en} {ayah.reference}
      </div>
    </section>
  );
}

function verificationTone(status: string): "warn" | "accent" | undefined {
  if (status === "VERIFIED") return "accent";
  if (status === "UNVERIFIED" || status === "MACHINE_PROPOSED") return "warn";
  return undefined;
}

function PassageBlock({
  passage,
  language,
  translation,
  translationPending,
}: {
  passage: Passage;
  language: UiLanguage;
  translation: PassageTranslation | null;
  translationPending: boolean;
}) {
  const t = COPY[language];
  const showTranslation = language !== "ar";

  return (
    <article className="passage">
      <div className="passage-marker" aria-hidden="true">
        [{passage.reference_number}]
      </div>

      {/* The source, always in the language the Mufassir wrote in. */}
      <div className="passage-original">
        {showTranslation && <div className="text-label">{t.originalArabic}</div>}
        <p className="passage-text" lang={passage.text_language} dir="rtl">
          {passage.text}
        </p>
      </div>

            <TranslateButton
        passageId={passage.passage_id}
        language={language}
        initial={translation ?? passage.translation ?? null}
      />

      <ProvenanceLadder citation={passage.citation} language={language} />

      <div className="citation">{passage.citation.reference}</div>

      <div className="chips">
        <span className="chip">{passage.evidence_type.replaceAll("_", " ")}</span>
        <span className="chip" data-tone={verificationTone(passage.verification_status)}>
          {passage.verification_status.replaceAll("_", " ")}
        </span>
        {passage.ayah && <span className="chip">{passage.ayah}</span>}
        {passage.retrieval_strategies.map((s) => (
          <span key={s} className="chip">
            {s}
          </span>
        ))}
      </div>
    </article>
  );
}

export function WorkGroup({
  work,
  language,
  translations,
  pending,
}: {
  work: Work;
  language: UiLanguage;
  translations: Record<string, PassageTranslation>;
  pending: Set<string>;
}) {
  const t = COPY[language];
  const author = language === "ar" ? work.author_ar : work.author_en ?? work.author_ar;
  const title = language === "ar" ? work.title_ar : work.title_en ?? work.title_ar;

  return (
    <section className="work-group reveal">
      <header className="work-head">
        <span className="work-author">{author}</span>
        {language !== "ar" && (
          <span className="work-author-ar" lang="ar" dir="rtl">
            {work.author_ar}
          </span>
        )}
        <span className="work-date">
          {work.author_death_year_hijri !== null
            ? `${t.died} ${work.author_death_year_hijri} AH`
            : t.dateUnverified}
        </span>
        <span className="work-title">{title}</span>
      </header>

      {work.passages.map((p) => (
        <PassageBlock
          key={p.passage_id}
          passage={p}
          language={language}
          translation={p.translation ?? translations[p.passage_id] ?? null}
          translationPending={pending.has(p.passage_id)}
        />
      ))}
    </section>
  );
}
