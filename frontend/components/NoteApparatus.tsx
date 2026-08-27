import { COPY } from "@/lib/i18n";
import type { ReadingNote, UiLanguage } from "@/lib/types";

/* The auditing apparatus for one passage.
 *
 * Everything here is already on the page at other depths, implicitly: which
 * clause a passage was attached to, how confidently, how far its citation
 * resolves, how much of that commentator's discussion is being shown. Auditing
 * depth stops implying it and states it.
 *
 * The ladder is drawn from what the corpus actually has. A hollow dot is not a
 * styling choice; it is the corpus saying this link does not exist. No edition
 * in the corpus has page images loaded, so the scan step is hollow everywhere,
 * and saying so plainly is better than a ladder that appears to reach the end.
 */

const LADDER = ["work", "edition", "volume", "page", "scan"] as const;

export function NoteApparatus({
  note,
  language,
}: {
  note: ReadingNote;
  language: UiLanguage;
}) {
  const t = COPY[language];
  const labels = t.ladder;

  const resolved: Record<(typeof LADDER)[number], boolean> = {
    work: Boolean(note.work_slug),
    // The edition on record is a digital text whose underlying print edition
    // the upstream source does not identify. Marking this step resolved was
    // wrong: it made the ladder claim an identified edition the corpus does
    // not have, which is the first thing a scholar checks and the worst place
    // to be caught overstating.
    edition: false,
    volume: note.volume !== null,
    page: note.page_start !== null,
    scan: false,
  };

  const inferred = note.alignment_basis === "OVERLAP";
  const held = Math.max(0, note.available_from_work - 1);

  return (
    <div className="apparatus">
      <div
        className="ladder"
        role="img"
        aria-label={`Citation resolves through ${
          LADDER.filter((s) => resolved[s]).length
        } of ${LADDER.length} stages`}
      >
        {LADDER.map((step, i) => (
          <span key={step} style={{ display: "contents" }}>
            {i > 0 && (
              <span
                className="ladder-link"
                data-resolved={resolved[LADDER[i - 1]] && resolved[step]}
                aria-hidden="true"
              />
            )}
            <span
              className="ladder-step"
              data-resolved={resolved[step]}
              aria-hidden="true"
            >
              <span className="ladder-dot" />
              <span className="ladder-name">{labels[step]}</span>
            </span>
          </span>
        ))}
      </div>

      <dl className="apparatus-grid">
        <div>
          <dt>{t.auditBasis}</dt>
          <dd data-tone={inferred ? "warn" : undefined}>
            {t.basisName(note.alignment_basis)}
          </dd>
        </div>
        <div>
          <dt>{t.auditConfidence}</dt>
          <dd>{note.alignment_confidence.toFixed(2)}</dd>
        </div>
        <div>
          <dt>{t.auditShowing}</dt>
          <dd>{held > 0 ? t.auditHeldBack(held) : t.auditAllShown}</dd>
        </div>
      </dl>

      <p className="apparatus-citation">{note.citation}</p>
      <p className="apparatus-limit">{t.auditNoPrintEdition}</p>
    </div>
  );
}
