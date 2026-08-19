import type { Ayah, Passage, UiLanguage, Work } from "@/lib/types";
import { COPY } from "@/lib/i18n";
import { ProvenanceLadder } from "./ProvenanceLadder";
import { TranslationPanel } from "./TranslationPanel";

/* Quranic text is rendered by its own component, in its own colour, in its own
 * block. It is never a card in the evidence list, because it is not evidence
 * about the ayah — it is the ayah. */

export function AyahBlock({ ayah, language }: { ayah: Ayah; language: UiLanguage }) {
  const t = COPY[language];
  return (
    <section className="ayah reveal" aria-label={`${t.ayahHeading} ${ayah.reference}`}>
      <div className="ayah-label">{t.ayahHeading}</div>
      <p className="ayah-text" lang="ar" dir="rtl">
        {ayah.text_uthmani}
      </p>
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

function PassageBlock({ passage, language }: { passage: Passage; language: UiLanguage }) {
  return (
    <article className="passage">
      <p className="passage-text" lang="ar" dir="rtl">
        {passage.text}
      </p>

      <ProvenanceLadder citation={passage.citation} language={language} />

      <div className="citation">{passage.citation.reference}</div>

      {/* Arabic readers already have the source; a translation into the source
          language would be a round trip through a model for no gain. */}
      {language !== "ar" && (
        <TranslationPanel passageId={passage.passage_id} language={language} />
      )}

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

export function WorkGroup({ work, language }: { work: Work; language: UiLanguage }) {
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
        <PassageBlock key={p.passage_id} passage={p} language={language} />
      ))}
    </section>
  );
}
