export type UiLanguage = "en" | "ar" | "ur";

export interface Citation {
  passage_id: string;
  work_slug: string;
  work_title_ar: string;
  work_title_en: string | null;
  author_name_ar: string;
  author_name_en: string | null;
  author_death_year_hijri: number | null;
  edition_slug: string;
  volume: number | null;
  page_start: number | null;
  page_end: number | null;
  scan_page_uri: string | null;
  resolves_to_page: boolean;
  citation_precision: string;
  reference: string;
}

export interface Passage {
  passage_id: string;
  text: string;
  evidence_type: string;
  verification_status: string;
  ayah: string | null;
  citation: Citation;
  retrieval_strategies: string[];
  fused_score: number;
}

export interface Work {
  work_slug: string;
  title_ar: string;
  title_en: string | null;
  author_ar: string;
  author_en: string | null;
  author_death_year_hijri: number | null;
  has_page_level_citation: boolean;
  passages: Passage[];
}

export interface Ayah {
  reference: string;
  surah_number: number;
  ayah_number: number;
  surah_name_ar: string;
  surah_name_en: string;
  text_uthmani: string;
  evidence_type: string;
}

export interface Trace {
  strategies_run: string[];
  candidates_per_strategy: Record<string, number>;
  filters_applied: Record<string, unknown>;
  fused_candidates: number;
  returned: number;
  works_represented: number;
  rules_applied: { rule: string; name: string; tier: string; provenance: string; scholarly: string }[];
}

export interface QueryResult {
  query: string;
  user_language: string;
  pivot_query: string;
  query_type: string;
  classification_confidence: number;
  references: string[];
  ayahs: Ayah[];
  works: Work[];
  passage_count: number;
  page_level_citation_coverage: number;
  notes: string[];
  trace: Trace;
  insufficient_evidence: boolean;
}
