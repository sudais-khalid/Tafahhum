"use client";

import { useState } from "react";
import { COPY } from "@/lib/i18n";
import type { TranslationResult, UiLanguage } from "@/lib/types";

const API = process.env.TAFAHHUM_API ?? "http://127.0.0.1:8000";

/* Passage translation.
 *
 * The Arabic stays on screen above this panel at all times. A translation is
 * additive — it never replaces the source, and it is always labelled with who
 * or what produced it, because a machine translation of classical exegesis is
 * an interpretation and must not be mistaken for the Mufassir's words. */

export function TranslationPanel({
  passageId,
  language,
}: {
  passageId: string;
  language: UiLanguage;
}) {
  const t = COPY[language];
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  async function load() {
    if (result) {
      setOpen((o) => !o);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API}/api/v1/passages/${passageId}/translate?language=${language}`,
        { method: "POST" },
      );
      if (res.status === 503) {
        setError(t.translationUnavailable);
        return;
      }
      if (!res.ok) throw new Error(String(res.status));
      setResult((await res.json()) as TranslationResult);
      setOpen(true);
    } catch {
      setError(t.translationFailed);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="translation">
      <button type="button" className="translate-btn" onClick={() => void load()} disabled={loading}>
        {loading
          ? t.translating
          : open
            ? t.hideTranslation
            : t.showTranslation(t.languageName)}
      </button>

      {error && <p className="translation-error">{error}</p>}

      {result && open && (
        <div className="translation-body reveal">
          <div className="translation-label">
            {t.translationInto(t.languageName)}
            {result.is_machine_translation && (
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
            {result.text}
          </p>
          <p className="translation-notice">
            {result.notice}
            {result.model_name ? ` · ${result.translator_name} (${result.model_name})` : ""}
          </p>
        </div>
      )}
    </div>
  );
}
