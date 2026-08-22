import type { QueryResult, UiLanguage } from "@/lib/types";
import { COPY } from "@/lib/i18n";

/* "How this answer was built".
 *
 * Shows system decisions and evidence counts: which strategies ran, how many
 * candidates each produced, and which rules fired with what they are grounded
 * in. It deliberately exposes no model reasoning, the useful thing to audit is
 * the retrieval path, not a narration of it. */

export function TracePanel({ result, language }: { result: QueryResult; language: UiLanguage }) {
  const t = COPY[language];
  const { trace } = result;

  return (
    <details className="trace">
      <summary>{t.howBuilt}</summary>
      <div className="trace-body">
        <dl className="trace-grid">
          <div className="trace-item">
            <dt>{t.queryType}</dt>
            <dd>
              {result.query_type} · {(result.classification_confidence * 100).toFixed(0)}%
            </dd>
          </div>
          <div className="trace-item">
            <dt>{t.pivotQuery}</dt>
            <dd lang="ar" dir="rtl">
              {result.pivot_query || "-"}
            </dd>
          </div>
          <div className="trace-item">
            <dt>{t.strategies}</dt>
            <dd>{trace.strategies_run.join(" + ") || "-"}</dd>
          </div>
          <div className="trace-item">
            <dt>{t.candidates}</dt>
            <dd>
              {Object.entries(trace.candidates_per_strategy)
                .map(([k, v]) => `${k} ${v}`)
                .join(" · ") || "-"}
            </dd>
          </div>
          <div className="trace-item">
            <dt>{t.worksRepresented}</dt>
            <dd>
              {trace.works_represented} / {trace.fused_candidates} fused
            </dd>
          </div>
        </dl>

        <dt
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "0.66rem",
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: "var(--ink-faint)",
            marginBottom: "0.4rem",
          }}
        >
          {t.rulesApplied} ({trace.rules_applied.length})
        </dt>
        <ul className="rule-list">
          {trace.rules_applied.map((r) => (
            <li key={r.rule} className="rule-row">
              <span className="rule-key">{r.rule}</span>
              <span>{r.name}</span>
              <span className="rule-prov">{r.provenance}</span>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
