"use client";

import { useEffect, useRef, useState } from "react";
import { COPY } from "@/lib/i18n";
import type { PassageTranslation, UiLanguage } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_TAFAHHUM_API ?? "";

/* One passage, translated on request.
 *
 * Shared by the reading view and the evidence view so that asking for a
 * translation feels the same wherever a reader meets a passage.
 *
 * On request rather than automatically: a page carries a dozen passages, and
 * translating all of them costs a dozen model calls the reader may not want.
 * The Arabic is present either way, so nothing is withheld by waiting to be
 * asked.
 */

export function TranslateButton({
  passageId,
  language,
  initial,
  autoOpen = false,
}: {
  passageId: string;
  language: UiLanguage;
  initial?: PassageTranslation | null;
  /** Fetch without waiting to be asked. Learning depth sets this, because
   *  there the translation is the content rather than an extra. */
  autoOpen?: boolean;
}) {
  const t = COPY[language];
  const [translation, setTranslation] = useState<PassageTranslation | null>(
    initial ?? null,
  );
  const [open, setOpen] = useState(Boolean(initial));
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  // Requested once per passage per mount. Without this guard, a re-render
  // while the request is in flight queues a second identical model call.
  const asked = useRef(false);

  useEffect(() => {
    if (!autoOpen || asked.current || translation || language === "ar") return;
    asked.current = true;
    void toggle();
    // toggle closes over state that does not change the decision to fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoOpen, language, translation]);

  // Arabic readers already have the source in front of them.
  if (language === "ar") return null;

  async function toggle() {
    if (translation) {
      setOpen((o) => !o);
      return;
    }
    setLoading(true);
    setProblem(null);
    try {
      const res = await fetch(
        `${API}/api/v1/passages/${passageId}/translate?language=${language}`,
        { method: "POST" },
      );
      if (res.status === 503) {
        setProblem(t.translationUnavailable);
        return;
      }
      if (!res.ok) throw new Error(String(res.status));
      const body = await res.json();
      if (!body.text) {
        setProblem(body.note ?? t.translationRejected);
        return;
      }
      setTranslation({
        text: body.text,
        language: body.language,
        translator_kind: body.translator_kind,
        translator_name: body.translator_name,
        model_name: body.model_name,
        verification_status: body.verification_status,
        is_machine: body.is_machine_translation,
        note: body.note ?? null,
      });
      setOpen(true);
    } catch {
      setProblem(t.translationFailed);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="translate-block">
      <button
        type="button"
        className="translate-cta"
        onClick={() => void toggle()}
        disabled={loading}
      >
        {loading ? (
          <>
            <span className="spinner-dark" aria-hidden="true" /> {t.translating}
          </>
        ) : open ? (
          t.hideTranslation
        ) : (
          t.showTranslation(t.languageName)
        )}
      </button>

      {problem && <p className="translate-problem">{problem}</p>}

      {translation && open && (
        <div className="translate-body reveal">
          <div className="text-label">
            {t.translationInto(t.languageName)}
            {translation.is_machine && (
              <span className="chip" data-tone="warn">
                {t.machineTranslation}
              </span>
            )}
          </div>
          <p
            className="translation-text"
            lang={language}
            dir={language === "en" ? "ltr" : "rtl"}
          >
            {translation.text}
          </p>
        </div>
      )}
    </div>
  );
}
