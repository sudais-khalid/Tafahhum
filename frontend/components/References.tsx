import type { Reference, UiLanguage } from "@/lib/types";
import { COPY } from "@/lib/i18n";

/* The reference list.
 *
 * Every source consulted for this query, numbered, with the provenance a reader
 * needs to check it: which edition was indexed, where that edition came from,
 * what its licence status is, and how far a citation into it actually resolves.
 *
 * Gaps are stated rather than omitted. A missing death year reads "not yet
 * verified" and not a blank, because a blank invites the reader to assume the
 * date is simply unimportant rather than unestablished. */

export function References({
  references,
  language,
  pageCoverage,
}: {
  references: Reference[];
  language: UiLanguage;
  pageCoverage: number;
}) {
  const t = COPY[language];
  if (references.length === 0) return null;

  return (
    <section className="references" aria-labelledby="refs-heading">
      <div className="section-head">
        <h2 id="refs-heading">{t.referencesHeading}</h2>
        <span className="count">{t.sourcesConsulted(references.length)}</span>
      </div>

      <ol className="ref-list">
        {references.map((r) => {
          const author =
            language === "ar" ? r.author_name_ar : r.author_name_en ?? r.author_name_ar;
          const title =
            language === "ar" ? r.work_title_ar : r.work_title_en ?? r.work_title_ar;

          return (
            <li className="ref-item" key={r.work_slug}>
              <span className="ref-number">[{r.number}]</span>

              <div className="ref-body">
                <div className="ref-title">
                  <strong>{author}</strong>
                  {" — "}
                  {title}
                </div>
                <div className="ref-title-ar" lang="ar" dir="rtl">
                  {r.author_name_ar} — {r.work_title_ar}
                </div>

                <dl className="ref-fields">
                  <div>
                    <dt>{t.refDied}</dt>
                    <dd>
                      {r.author_death_year_hijri !== null
                        ? `${r.author_death_year_hijri} AH`
                        : t.dateUnverified}
                    </dd>
                  </div>
                  <div>
                    <dt>{t.refEdition}</dt>
                    <dd>
                      {r.edition_publisher ?? t.refNoPrintEdition}
                      {r.edition_year ? ` (${r.edition_year})` : ""}
                    </dd>
                  </div>
                  <div>
                    <dt>{t.refPassages}</dt>
                    <dd>{r.passages_cited}</dd>
                  </div>
                  <div>
                    <dt>{t.refCitationDepth}</dt>
                    <dd>{r.resolves_to_page ? t.refToPage : t.refToWork}</dd>
                  </div>
                  <div>
                    <dt>{t.refRights}</dt>
                    <dd>{r.copyright_status.replaceAll("_", " ").toLowerCase()}</dd>
                  </div>
                  <div>
                    <dt>{t.refVerification}</dt>
                    <dd>{r.verification_status.replaceAll("_", " ").toLowerCase()}</dd>
                  </div>
                </dl>

                {r.digital_source_url && (
                  <a
                    className="ref-source"
                    href={r.digital_source_url}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    {t.refOpenSource}
                  </a>
                )}

                {r.license_note && <p className="ref-licence">{r.license_note}</p>}
              </div>
            </li>
          );
        })}
      </ol>

      <p className="ref-summary">
        {t.refCoverage(Math.round(pageCoverage * 100))}
      </p>
    </section>
  );
}
