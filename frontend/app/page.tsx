"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AyahBlock, WorkGroup } from "@/components/Evidence";
import { References } from "@/components/References";
import { SourceSelector } from "@/components/SourceSelector";
import { TracePanel } from "@/components/TracePanel";
import { COPY, DIR, LANGUAGES } from "@/lib/i18n";
import type { PassageTranslation, QueryResult, UiLanguage } from "@/lib/types";

const API = process.env.TAFAHHUM_API ?? "http://127.0.0.1:8000";

/** Concurrent translation requests. Kept low so a twelve-passage result does not
 *  open twelve simultaneous model calls against the server. */
const TRANSLATION_CONCURRENCY = 3;

export default function Home() {
  const [language, setLanguage] = useState<UiLanguage>("en");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Translations that arrived after the initial response.
  const [translations, setTranslations] = useState<Record<string, PassageTranslation>>({});
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [translationNotice, setTranslationNotice] = useState<string | null>(null);
  // Which works retrieval is restricted to. `null` means "not yet loaded"; the
  // selector fills it from the default preset on mount.
  const [sources, setSources] = useState<string[] | null>(null);
  const runId = useRef(0);

  const t = COPY[language];
  const dir = DIR[language];

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [language, dir]);

  const search = useCallback(
    async (text: string) => {
      const query = text.trim();
      if (!query) return;

      const thisRun = ++runId.current;
      setLoading(true);
      setError(null);
      setTranslations({});
      setPending(new Set());
      setTranslationNotice(null);

      try {
        const res = await fetch(`${API}/api/v1/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            language,
            mode: "DETAILED",
            works: sources && sources.length > 0 ? sources : undefined,
          }),
        });
        if (!res.ok) throw new Error(String(res.status));
        const data = (await res.json()) as QueryResult;
        if (thisRun !== runId.current) return;
        setResult(data);
        void fillTranslations(data, thisRun);
      } catch {
        if (thisRun === runId.current) {
          setError(t.error);
          setResult(null);
        }
      } finally {
        if (thisRun === runId.current) setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [language, t.error, sources],
  );

  /* Request the translations the server did not already have cached.
   *
   * The Arabic is on screen throughout; translations fill in beneath it as they
   * arrive, so a slow or unavailable backend never blocks the evidence. */
  const fillTranslations = useCallback(
    async (data: QueryResult, thisRun: number) => {
      if (language === "ar") return;
      const missing = data.untranslated_passage_ids;
      if (missing.length === 0) return;

      setPending(new Set(missing));
      const queue = [...missing];
      let backendMissing = false;

      async function worker() {
        while (queue.length > 0) {
          const id = queue.shift();
          if (!id || thisRun !== runId.current) return;
          try {
            const res = await fetch(
              `${API}/api/v1/passages/${id}/translate?language=${language}`,
              { method: "POST" },
            );
            if (res.status === 503) {
              backendMissing = true;
              queue.length = 0;
              return;
            }
            if (!res.ok) continue;
            const body = await res.json();
            if (thisRun !== runId.current) return;
            setTranslations((prev) => ({
              ...prev,
              [id]: {
                text: body.text,
                language: body.language,
                translator_kind: body.translator_kind,
                translator_name: body.translator_name,
                model_name: body.model_name,
                verification_status: body.verification_status,
                is_machine: body.is_machine_translation,
                note: body.note ?? null,
              },
            }));
          } finally {
            if (thisRun === runId.current) {
              setPending((prev) => {
                const next = new Set(prev);
                next.delete(id);
                return next;
              });
            }
          }
        }
      }

      await Promise.all(
        Array.from({ length: Math.min(TRANSLATION_CONCURRENCY, queue.length) }, worker),
      );

      if (thisRun === runId.current) {
        setPending(new Set());
        if (backendMissing) setTranslationNotice(t.translationUnavailable);
      }
    },
    [language, t.translationUnavailable],
  );

  return (
    <div className="shell">
      <header className="masthead">
        <div className="wrap masthead-inner">
          <a className="wordmark" href="/">
            <span className="wordmark-latin">Tafahhum</span>
            <span className="wordmark-arabic" lang="ar" dir="rtl">
              تَفَهُّم
            </span>
          </a>
          <span className="masthead-tagline">{t.tagline}</span>
        </div>
      </header>

      <main className="wrap">
        <section className="hero">
          <h1 className="hero-title">{t.heroTitle}</h1>
          <p className="hero-sub">{t.heroSub}</p>

          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              void search(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t.placeholder}
              aria-label={t.placeholder}
              dir="auto"
            />
            <button type="submit" disabled={loading || !input.trim()}>
              {loading ? (
                <>
                  <span className="spinner" aria-hidden="true" /> {t.searching}
                </>
              ) : (
                t.search
              )}
            </button>
          </form>

          <div className="search-meta">
            <span>{t.language}</span>
            <div className="lang-switch" role="group" aria-label={t.language}>
              {LANGUAGES.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  aria-pressed={language === l.code}
                  onClick={() => setLanguage(l.code)}
                  lang={l.code}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <SourceSelector
            language={language}
            selected={sources}
            onChange={(slugs) => setSources(slugs)}
          />

          <div className="examples">
            {t.examples.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setInput(ex);
                  void search(ex);
                }}
              >
                {ex}
              </button>
            ))}
          </div>
        </section>

        {error && <div className="notice">{error}</div>}

        {result && (
          <>
            {result.ayahs.map((a) => (
              <AyahBlock key={a.reference} ayah={a} language={language} />
            ))}

            {(result.notes.length > 0 || translationNotice) && (
              <div className="notice-list">
                {translationNotice && <div className="notice">{translationNotice}</div>}
                {result.notes.map((n) => (
                  <div className="notice" key={n}>
                    {n}
                  </div>
                ))}
              </div>
            )}

            <div className="section-head">
              <h2>{t.evidenceHeading}</h2>
              <span className="count">
                {t.passagesFrom(result.passage_count, result.works.length)}
              </span>
            </div>

            {result.insufficient_evidence ? (
              <div className="empty">
                <p style={{ marginTop: 0, fontWeight: 500 }}>{t.noEvidence}</p>
                <p style={{ marginBottom: 0, fontSize: "0.9rem" }}>{t.noEvidenceHint}</p>
              </div>
            ) : (
              result.works.map((w) => (
                <WorkGroup
                  key={w.work_slug}
                  work={w}
                  language={language}
                  translations={translations}
                  pending={pending}
                />
              ))
            )}

            <References
              references={result.references}
              language={language}
              pageCoverage={result.page_level_citation_coverage}
            />

            <TracePanel result={result} language={language} />
          </>
        )}
      </main>

      <footer className="footer">
        <div className="wrap">
          <p>{t.footerNote}</p>
          <p>{t.footerCorpus}</p>
        </div>
      </footer>
    </div>
  );
}
