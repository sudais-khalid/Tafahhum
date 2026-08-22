"use client";

import { useState } from "react";
import { COPY } from "@/lib/i18n";
import type { AyahSummary, UiLanguage } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_TAFAHHUM_API ?? "";

/* The generated conclusion.
 *
 * Everything else on the page is quoted; this is the one block that is written.
 * The design says so rather than letting it blend in: it sits apart, is labelled
 * as Tafahhum's own synthesis, and shows the verification counts inline instead
 * of tucking them behind a link.
 *
 * A summary that discarded three of its own sentences is more trustworthy than
 * one claiming none were discarded, so the filter's work is shown, not hidden.
 *
 * It is requested rather than loaded automatically: generation is slow on a
 * local model, and a reader who only wants the commentaries should not wait for
 * a summary they did not ask for. */

export function SummaryPanel({
  surah,
  ayah,
  language,
  works,
}: {
  surah: number;
  ayah: number;
  language: UiLanguage;
  works?: string[] | null;
}) {
  const t = COPY[language];
  const [data, setData] = useState<AyahSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRemoved, setShowRemoved] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ language });
      if (works && works.length > 0) params.set("works", works.join(","));
      const res = await fetch(
        `${API}/api/v1/read/${surah}/${ayah}/summary?${params}`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(String(res.status));
      setData((await res.json()) as AyahSummary);
    } catch {
      setError(t.summaryFailed);
    } finally {
      setLoading(false);
    }
  }

  const unavailable = data && data.status === "unavailable";
  const insufficient = data && data.status === "insufficient";

  return (
    <section className="synthesis">
      <div className="synthesis-head">
        <span className="synthesis-label">{t.synthesisLabel}</span>
        {!data && (
          <button type="button" onClick={() => void load()} disabled={loading}>
            {loading ? (
              <>
                <span className="spinner-dark" aria-hidden="true" /> {t.summarising}
              </>
            ) : (
              t.buildSummary
            )}
          </button>
        )}
      </div>

      <p className="synthesis-caveat">{t.synthesisCaveat}</p>

      {error && <p className="synthesis-problem">{error}</p>}

      {(unavailable || insufficient) && (
        <p className="synthesis-problem">{data?.reason}</p>
      )}

      {data?.summary && (
        <>
          <p
            className="synthesis-text"
            lang={language}
            dir={language === "en" ? "ltr" : "rtl"}
          >
            {data.summary}
          </p>

          {/* The filter's own record. Kept next to the text it produced, because
              a reader judging the summary needs to know what was cut from it. */}
          <dl className="synthesis-audit">
            <div>
              <dt>{t.sentencesWritten}</dt>
              <dd>{data.sentences_generated ?? "—"}</dd>
            </div>
            <div>
              <dt>{t.sentencesKept}</dt>
              <dd>{data.sentences_kept ?? "—"}</dd>
            </div>
            <div>
              <dt>{t.sentencesRemoved}</dt>
              <dd>{data.sentences_removed ?? "—"}</dd>
            </div>
            <div>
              <dt>{t.meanSupport}</dt>
              <dd>
                {data.mean_support != null
                  ? `${Math.round(data.mean_support * 100)}%`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt>{t.builtFrom}</dt>
              <dd>{data.cited_passage_ids?.length ?? 0}</dd>
            </div>
          </dl>

          {data.removed_detail && data.removed_detail.length > 0 && (
            <div className="synthesis-removed">
              <button type="button" onClick={() => setShowRemoved(!showRemoved)}>
                {showRemoved ? t.hideRemoved : t.showRemoved(data.removed_detail.length)}
              </button>
              {showRemoved && (
                <ul>
                  {data.removed_detail.map((r, i) => (
                    <li key={i}>
                      <span className="removed-reason">{r.reason}</span>
                      <span className="removed-text" lang="ar" dir="rtl">
                        {r.text}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <p className="synthesis-notice">{data.notice ?? t.synthesisNotice}</p>
        </>
      )}
    </section>
  );
}
