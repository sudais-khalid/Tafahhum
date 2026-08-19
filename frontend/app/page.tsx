"use client";

import { useCallback, useEffect, useState } from "react";
import { AyahBlock, WorkGroup } from "@/components/Evidence";
import { TracePanel } from "@/components/TracePanel";
import { COPY, DIR, LANGUAGES } from "@/lib/i18n";
import type { QueryResult, UiLanguage } from "@/lib/types";

const API = process.env.TAFAHHUM_API ?? "http://127.0.0.1:8000";

export default function Home() {
  const [language, setLanguage] = useState<UiLanguage>("en");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const t = COPY[language];
  const dir = DIR[language];

  // The document direction follows the interface language, so RTL layout is a
  // property of the page rather than something each component re-implements.
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [language, dir]);

  const search = useCallback(
    async (text: string) => {
      const query = text.trim();
      if (!query) return;

      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API}/api/v1/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, language, mode: "DETAILED" }),
        });
        if (!res.ok) throw new Error(String(res.status));
        setResult((await res.json()) as QueryResult);
      } catch {
        setError(t.error);
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [language, t.error],
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

            {result.notes.length > 0 && (
              <div className="notice-list">
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
                <WorkGroup key={w.work_slug} work={w} language={language} />
              ))
            )}

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
