"use client";

import { useEffect, useState } from "react";
import { DEPTHS, useDepth, type Depth } from "@/lib/depth";
import { GUIDE } from "@/lib/guide";
import { COPY, DIR, LANGUAGES } from "@/lib/i18n";
import type { UiLanguage } from "@/lib/types";

/* How it works.
 *
 * A page arguing that a reader can trust this system, which means it has to be
 * held to the same standard as everything else here: it may only claim what the
 * system does, and it must state the known gaps rather than leave a reader to
 * find them. The gaps section is not a disclaimer at the bottom; it is part of
 * the argument.
 */

export default function HowItWorks() {
  const [language, setLanguage] = useState<UiLanguage>("en");
  const [depth, setDepth] = useDepth();
  const g = GUIDE[language];
  const t = COPY[language];
  const dir = DIR[language];

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [language, dir]);

  const depthName: Record<Depth, string> = {
    learn: t.depthLearn,
    read: t.depthRead,
    audit: t.depthAudit,
  };

  return (
    <div className="shell" data-depth={depth}>
      <header className="masthead">
        <div className="wrap masthead-inner">
          <a className="wordmark" href="/">
            <span className="wordmark-latin">Tafahhum</span>
            <span className="wordmark-arabic" lang="ar" dir="rtl">
              تَفَهُّم
            </span>
          </a>

          <span className="masthead-divider" aria-hidden="true" />

          <div className="depth">
            <span className="depth-label">{t.depthLabel}</span>
            <div className="segmented" role="group" aria-label={t.depthLabel}>
              {DEPTHS.map((d) => (
                <button
                  key={d}
                  type="button"
                  aria-pressed={depth === d}
                  onClick={() => setDepth(d)}
                >
                  {depthName[d]}
                </button>
              ))}
            </div>
          </div>

          <span className="masthead-spacer" />

          <div className="segmented" data-tone="accent" role="group" aria-label={t.language}>
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
      </header>

      <main className="wrap guide">
        <a className="guide-back" href="/">
          {g.back}
        </a>

        <h1 className="guide-title">{g.title}</h1>
        <p className="guide-standfirst">{g.standfirst}</p>

        {/* The chain, which is the whole argument in one figure. */}
        <section className="guide-section">
          <h2 className="guide-h2">{g.chainTitle}</h2>
          <p className="guide-note">{g.chainNote}</p>
          <ol className="chain">
            {g.chain.map((c) => (
              <li className="chain-step" key={c.label}>
                <span className="chain-number" aria-hidden="true">
                  {c.step}
                </span>
                <div className="chain-body">
                  <h3 className="chain-label">{c.label}</h3>
                  <p className="chain-detail">{c.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {g.sections.map((s) => (
          <section className="guide-section" key={s.id} id={s.id}>
            <h2 className="guide-h2">{s.title}</h2>
            {s.body.map((p, i) => (
              <p className="guide-p" key={i}>
                {p}
              </p>
            ))}

            {s.controls && (
              <dl className="controls">
                {s.controls.map((c) => (
                  <div className="control" key={c.name}>
                    <dt>
                      <span className="control-name">{c.name}</span>
                      <span className="control-where">{c.where}</span>
                    </dt>
                    <dd>{c.detail}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        ))}

        <section className="guide-section">
          <h2 className="guide-h2">{g.neverTitle}</h2>
          <p className="guide-note">{g.neverNote}</p>
          <ul className="never-list">
            {g.never.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </section>

        {/* Deliberately not at the bottom as a disclaimer, and not omitted. */}
        <section className="guide-section">
          <h2 className="guide-h2">{g.gapsTitle}</h2>
          <p className="guide-note">{g.gapsNote}</p>
          <div className="gap-list">
            {g.gaps.map((gap) => (
              <div className="gap" key={gap.name}>
                <h3 className="gap-name">{gap.name}</h3>
                <p className="gap-detail">{gap.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="guide-section guide-check">
          <h2 className="guide-h2">{g.checkTitle}</h2>
          <ol className="check-list">
            {g.check.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ol>
        </section>
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
