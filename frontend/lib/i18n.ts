import type { UiLanguage } from "./types";

/* Interface copy in the three user languages.
 *
 * Only the interface is translated. Source passages stay in Arabic in every
 * language, because translating a quotation and presenting it as the source is
 * exactly what this system must not do. */

export const LANGUAGES: { code: UiLanguage; label: string; dir: "ltr" | "rtl" }[] = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "ar", label: "العربية", dir: "rtl" },
  { code: "ur", label: "اردو", dir: "rtl" },
];

export const DIR: Record<UiLanguage, "ltr" | "rtl"> = {
  en: "ltr",
  ar: "rtl",
  ur: "rtl",
};

type Copy = {
  tagline: string;
  heroTitle: string;
  heroSub: string;
  placeholder: string;
  search: string;
  searching: string;
  language: string;
  examples: string[];
  ayahHeading: string;
  evidenceHeading: string;
  passagesFrom: (p: number, w: number) => string;
  noEvidence: string;
  noEvidenceHint: string;
  howBuilt: string;
  queryType: string;
  pivotQuery: string;
  strategies: string;
  candidates: string;
  worksRepresented: string;
  rulesApplied: string;
  died: string;
  dateUnverified: string;
  ladder: { work: string; edition: string; volume: string; page: string; scan: string };
  footerNote: string;
  footerCorpus: string;
  error: string;
};

const en: Copy = {
  tagline: "Explore the legacy of Quranic interpretation.",
  heroTitle: "Read the Tafsir tradition at its source.",
  heroSub:
    "Ask about an ayah, a Mufassir, or a question of interpretation. Every passage returned comes from an indexed work and carries its provenance with it.",
  placeholder: "Ask about an ayah, Tafsir, Mufassir, or topic…",
  search: "Search",
  searching: "Searching",
  language: "Language",
  examples: [
    "What do the Tafasir say about 2:255?",
    "Compare Tabari and Qurtubi on 2:255",
    "Ayat al-Kursi",
    "occasion of revelation for 2:256",
  ],
  ayahHeading: "Quranic text",
  evidenceHeading: "Evidence from the corpus",
  passagesFrom: (p, w) => `${p} passages from ${w} works`,
  noEvidence: "Insufficient verified evidence was retrieved from the current corpus.",
  noEvidenceHint:
    "This ayah is not yet indexed. The corpus is built by ingestion, and coverage grows work by work.",
  howBuilt: "How this answer was built",
  queryType: "Question type",
  pivotQuery: "Arabic search terms",
  strategies: "Retrieval strategies",
  candidates: "Candidates found",
  worksRepresented: "Works represented",
  rulesApplied: "Rules applied",
  died: "d.",
  dateUnverified: "date not yet verified",
  ladder: { work: "Work", edition: "Edition", volume: "Volume", page: "Page", scan: "Scan" },
  footerNote:
    "Tafahhum organises and cites the Tafsir tradition. It does not author Tafsir, and it is not a substitute for qualified scholars.",
  footerCorpus: "Corpus coverage is partial and expanding. Absence of a source is not evidence of its silence.",
  error: "The search could not be completed. Check that the API is running, then try again.",
};

const ar: Copy = {
  tagline: "استكشف تراث التفسير القرآني.",
  heroTitle: "اقرأ تراث التفسير من مصادره.",
  heroSub:
    "اسأل عن آية أو مفسر أو مسألة تفسيرية. كل نص يُعرض مأخوذ من عمل مفهرس، ويحمل معه بيانات مصدره.",
  placeholder: "اسأل عن آية أو تفسير أو مفسر أو موضوع…",
  search: "ابحث",
  searching: "جارٍ البحث",
  language: "اللغة",
  examples: [
    "ما تفسير قوله تعالى الحي القيوم",
    "سورة البقرة الآية ٢٥٥",
    "قارن بين الطبري والقرطبي",
    "سبب النزول",
  ],
  ayahHeading: "النص القرآني",
  evidenceHeading: "الشواهد من المدونة",
  passagesFrom: (p, w) => `${p} نصًا من ${w} من الكتب`,
  noEvidence: "لم يُسترجع دليل موثّق كافٍ من المدونة الحالية.",
  noEvidenceHint: "هذه الآية غير مفهرسة بعد. تُبنى المدونة بالإدخال، وتتسع كتابًا بعد كتاب.",
  howBuilt: "كيف بُني هذا الجواب",
  queryType: "نوع السؤال",
  pivotQuery: "مصطلحات البحث العربية",
  strategies: "طرق الاسترجاع",
  candidates: "المرشحات",
  worksRepresented: "الكتب الممثَّلة",
  rulesApplied: "القواعد المطبَّقة",
  died: "ت.",
  dateUnverified: "التاريخ غير موثّق بعد",
  ladder: { work: "الكتاب", edition: "الطبعة", volume: "المجلد", page: "الصفحة", scan: "الصورة" },
  footerNote: "تفهّم ينظّم تراث التفسير ويوثّقه. وهو لا يؤلّف تفسيرًا، ولا يغني عن أهل العلم.",
  footerCorpus: "تغطية المدونة جزئية ومتنامية. وغياب المصدر ليس دليلًا على سكوته.",
  error: "تعذّر إتمام البحث. تأكد من تشغيل الخادم ثم أعد المحاولة.",
};

const ur: Copy = {
  tagline: "قرآنی تفسیر کے ورثے کی تلاش۔",
  heroTitle: "تفسیری روایت کو اس کے اصل مآخذ سے پڑھیے۔",
  heroSub:
    "کسی آیت، مفسر یا تفسیری مسئلے کے بارے میں پوچھیے۔ ہر عبارت کسی فہرست شدہ کتاب سے آتی ہے اور اپنے مآخذ کی تفصیل ساتھ رکھتی ہے۔",
  placeholder: "آیت، تفسیر، مفسر یا موضوع کے بارے میں پوچھیے…",
  search: "تلاش",
  searching: "تلاش جاری ہے",
  language: "زبان",
  examples: [
    "آیت الکرسی کی تفسیر کیا ہے؟",
    "سورہ بقرہ آیت ۲۵۵",
    "طبری اور قرطبی کا موازنہ",
    "شان نزول",
  ],
  ayahHeading: "قرآنی متن",
  evidenceHeading: "مجموعے سے شواہد",
  passagesFrom: (p, w) => `${w} کتابوں سے ${p} عبارات`,
  noEvidence: "موجودہ مجموعے سے کافی مستند شواہد نہیں ملے۔",
  noEvidenceHint: "یہ آیت ابھی فہرست میں شامل نہیں۔ مجموعہ کتاب بہ کتاب بڑھایا جا رہا ہے۔",
  howBuilt: "یہ جواب کیسے بنا",
  queryType: "سوال کی نوعیت",
  pivotQuery: "عربی تلاش الفاظ",
  strategies: "بازیابی کے طریقے",
  candidates: "امیدوار عبارات",
  worksRepresented: "شامل کتابیں",
  rulesApplied: "لاگو قواعد",
  died: "وفات",
  dateUnverified: "تاریخ ابھی مستند نہیں",
  ladder: { work: "کتاب", edition: "ایڈیشن", volume: "جلد", page: "صفحہ", scan: "عکس" },
  footerNote:
    "تفہّم تفسیری ورثے کو مرتب اور مستند کرتا ہے۔ یہ خود تفسیر نہیں لکھتا، اور اہلِ علم کا بدل نہیں۔",
  footerCorpus: "مجموعے کا احاطہ جزوی اور بڑھتا ہوا ہے۔ کسی مآخذ کا نہ ہونا اس کی خاموشی کی دلیل نہیں۔",
  error: "تلاش مکمل نہ ہو سکی۔ سرور چل رہا ہے یا نہیں، جانچ کر دوبارہ کوشش کریں۔",
};

export const COPY: Record<UiLanguage, Copy> = { en, ar, ur };
