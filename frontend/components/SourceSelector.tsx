"use client";

import { useEffect, useMemo, useState } from "react";
import { COPY } from "@/lib/i18n";
import type { CatalogueResponse, CatalogueWork, UiLanguage } from "@/lib/types";

const API = process.env.TAFAHHUM_API ?? "http://127.0.0.1:8000";

/* Choosing sources.
 *
 * Fifty works is too many to pick from cold, so presets carry the common cases
 * and the full list is there when someone wants it. The two are the same
 * control: choosing a preset selects works, and adjusting works from there is
 * expected rather than an escape hatch.
 *
 * Classification is shown with its provenance. A reader filtering by school is
 * filtering on a tertiary reference, and the panel says so rather than letting
 * the filter imply a scholarly judgement Tafahhum has not made. */

const TRADITION_ORDER = [
  "EARLY",
  "SUNNI",
  "SUNNI_SUFI",
  "SUNNI_SALAFI",
  "MODERNIST",
  "MUTAZILA",
  "TWELVER_SHIA",
  "ZAYDI_SHIA",
  "IBADI",
  "UNCLASSIFIED",
];

export function SourceSelector({
  language,
  selected,
  onChange,
}: {
  language: UiLanguage;
  selected: string[] | null;
  onChange: (slugs: string[] | null, presetKey: string | null) => void;
}) {
  const t = COPY[language];
  const [data, setData] = useState<CatalogueResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [activePreset, setActivePreset] = useState<string | null>("sunni-core");

  useEffect(() => {
    fetch(`${API}/api/v1/catalogue`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: CatalogueResponse | null) => {
        if (!d) return;
        setData(d);
        // Start from the default preset so a first-time visitor gets a
        // deliberate selection rather than the whole corpus or nothing.
        const preset = d.presets.find((p) => p.key === "sunni-core");
        if (preset && selected === null) onChange(preset.work_slugs, preset.key);
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grouped = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, CatalogueWork[]>();
    for (const w of data.works) {
      const list = map.get(w.tradition) ?? [];
      list.push(w);
      map.set(w.tradition, list);
    }
    return TRADITION_ORDER.filter((k) => map.has(k)).map((k) => ({
      tradition: k,
      works: map.get(k)!,
    }));
  }, [data]);

  if (!data) return null;

  const chosen = new Set(selected ?? []);

  function applyPreset(key: string) {
    const preset = data!.presets.find((p) => p.key === key);
    if (!preset) return;
    setActivePreset(key);
    onChange(preset.work_slugs, key);
  }

  function toggleWork(slug: string) {
    const next = new Set(chosen);
    if (next.has(slug)) next.delete(slug);
    else next.add(slug);
    setActivePreset(null);
    onChange([...next], null);
  }

  const totalPassages = data.works
    .filter((w) => chosen.has(w.slug))
    .reduce((n, w) => n + w.passage_count, 0);

  return (
    <section className="sources">
      <div className="sources-summary">
        <span className="sources-count">
          {t.sourcesSelected(chosen.size, data.counts.works, totalPassages)}
        </span>
        <button type="button" className="sources-toggle" onClick={() => setOpen(!open)}>
          {open ? t.sourcesHide : t.sourcesChoose}
        </button>
      </div>

      <div className="preset-row">
        {data.presets.map((p) => (
          <button
            key={p.key}
            type="button"
            className="preset"
            aria-pressed={activePreset === p.key}
            onClick={() => applyPreset(p.key)}
            title={p.description_en}
          >
            {language === "ar" ? p.name_ar : language === "ur" ? p.name_ur : p.name_en}
            <span className="preset-count">{p.work_count}</span>
          </button>
        ))}
      </div>

      {open && (
        <div className="source-list reveal">
          <p className="source-note">{t.classificationNote}</p>

          {grouped.map((group) => (
            <div className="source-group" key={group.tradition}>
              <h3 className="source-group-head">
                {t.tradition(group.tradition)}
                <span className="source-group-count">{group.works.length}</span>
              </h3>

              <div className="source-grid">
                {group.works.map((w) => (
                  <label className="source-item" key={w.slug}>
                    <input
                      type="checkbox"
                      checked={chosen.has(w.slug)}
                      onChange={() => toggleWork(w.slug)}
                    />
                    <span className="source-body">
                      <span className="source-title">
                        {language === "ar" ? w.title_ar : w.title_en ?? w.title_ar}
                      </span>
                      <span className="source-author">
                        {language === "ar"
                          ? w.author_ar
                          : w.author_en ?? w.author_ar}
                        {w.death_year_hijri ? ` · ${t.died} ${w.death_year_hijri} AH` : ""}
                      </span>
                      <span className="source-meta">
                        {t.method(w.method)} · {w.passage_count} {t.passagesWord}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
