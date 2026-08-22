import type { Citation, UiLanguage } from "@/lib/types";
import { COPY } from "@/lib/i18n";

/* The provenance ladder.
 *
 * Shows how far a citation actually resolves, from the work down to the
 * scanned page. A hollow dot is not a styling choice, it is the corpus
 * telling the reader that this link in the chain does not exist yet.
 *
 * Putting this on every passage rather than in a footnote means a limitation
 * can never be missed by a reader who is skimming. */

const STEPS = ["work", "edition", "volume", "page", "scan"] as const;

export function ProvenanceLadder({
  citation,
  language,
}: {
  citation: Citation;
  language: UiLanguage;
}) {
  const labels = COPY[language].ladder;

  const resolved: Record<(typeof STEPS)[number], boolean> = {
    work: Boolean(citation.work_slug),
    edition: Boolean(citation.edition_slug),
    volume: citation.volume !== null,
    page: citation.page_start !== null,
    scan: Boolean(citation.scan_page_uri),
  };

  const reached = STEPS.filter((s) => resolved[s]).length;

  return (
    <div
      className="ladder"
      role="img"
      aria-label={`Citation resolves through ${reached} of ${STEPS.length} stages: ${STEPS.filter(
        (s) => resolved[s],
      )
        .map((s) => labels[s])
        .join(", ")}`}
    >
      {STEPS.map((step, i) => (
        <span key={step} style={{ display: "contents" }}>
          {i > 0 && (
            <span
              className="ladder-link"
              data-resolved={resolved[STEPS[i - 1]] && resolved[step]}
              aria-hidden="true"
            />
          )}
          <span className="ladder-step" data-resolved={resolved[step]} aria-hidden="true">
            <span className="ladder-dot" />
            <span className="ladder-name">{labels[step]}</span>
          </span>
        </span>
      ))}
    </div>
  );
}
