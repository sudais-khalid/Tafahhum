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
  languageName: string;
  originalArabic: string;
  translationPendingNote: string;
  translationSlowNote: string;
  translationRejected: string;
  sourcesChoose: string;
  sourcesHide: string;
  sourcesSelected: (n: number, total: number, passages: number) => string;
  classificationNote: string;
  passagesWord: string;
  tradition: (key: string) => string;
  method: (key: string) => string;
  referencesHeading: string;
  sourcesConsulted: (n: number) => string;
  refDied: string;
  refEdition: string;
  refNoPrintEdition: string;
  refPassages: string;
  refCitationDepth: string;
  refToPage: string;
  refToWork: string;
  refRights: string;
  refVerification: string;
  refOpenSource: string;
  refCoverage: (pct: number) => string;
  showTranslation: (lang: string) => string;
  hideTranslation: string;
  translating: string;
  translationInto: (lang: string) => string;
  machineTranslation: string;
  translationUnavailable: string;
  translationFailed: string;
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
  languageName: "English",
  originalArabic: "Original (Arabic)",
  translationPendingNote:
    "No translation stored for this passage yet. The Arabic above is the source.",
  translationSlowNote:
    "Translating on the local model — this takes a few minutes per passage on CPU. The Arabic above is complete and unaffected.",
  translationRejected:
    "The local model produced unusable output for this language and it was discarded rather than shown.",
  sourcesChoose: "Choose sources",
  sourcesHide: "Hide sources",
  sourcesSelected: (n, total, passages) =>
    `${n} of ${total} works selected · ${passages.toLocaleString()} passages searched`,
  classificationNote:
    "School and method come from a tertiary reference and are unverified. Works that reference does not list are shown as unclassified rather than assigned a school by inference.",
  passagesWord: "passages",
  tradition: (k) =>
    ({
      EARLY: "Early",
      SUNNI: "Sunni",
      SUNNI_SUFI: "Sunni — Sufi",
      SUNNI_SALAFI: "Sunni — Salafi",
      MODERNIST: "Modernist",
      MUTAZILA: "Mu'tazila",
      TWELVER_SHIA: "Twelver Shia",
      ZAYDI_SHIA: "Zaydi Shia",
      IBADI: "Ibadi",
      UNCLASSIFIED: "Classification pending",
    })[k] ?? k,
  method: (k) =>
    ({
      BI_AL_MATHUR: "transmitted reports",
      BI_AL_RAY: "considered opinion",
      FIQHI: "legal",
      LUGHAWI: "linguistic",
      BALAGHI: "rhetorical",
      SUFI_ISHARI: "allusive",
      KALAMI: "theological",
      QIRAAT: "variant readings",
      GHARIB: "rare vocabulary",
      MIXED: "mixed method",
      UNCLASSIFIED: "method not recorded",
    })[k] ?? k,
  referencesHeading: "References",
  sourcesConsulted: (n) => `${n} sources consulted`,
  refDied: "Died",
  refEdition: "Edition",
  refNoPrintEdition: "digital text, no print edition identified",
  refPassages: "Passages cited",
  refCitationDepth: "Citation resolves to",
  refToPage: "volume and page",
  refToWork: "the work only",
  refRights: "Rights",
  refVerification: "Verification",
  refOpenSource: "Open source record",
  refCoverage: (pct) =>
    `${pct}% of cited passages resolve to a printed page. The rest resolve to the work and edition only.`,
  showTranslation: (lang) => `Translate into ${lang}`,
  hideTranslation: "Hide translation",
  translating: "Translating…",
  translationInto: (lang) => `${lang} translation`,
  machineTranslation: "machine translation",
  translationUnavailable:
    "No translation backend is configured on the server. The Arabic above is the source and is unaffected.",
  translationFailed: "The translation could not be produced. The Arabic above is unaffected.",
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
  languageName: "العربية",
  originalArabic: "النص الأصلي",
  translationPendingNote: "لا توجد ترجمة مخزنة بعد. والنص العربي أعلاه هو الأصل.",
  translationSlowNote:
    "الترجمة جارية على النموذج المحلي، وتستغرق دقائق لكل نص. والنص العربي أعلاه كامل وغير متأثر.",
  translationRejected: "أنتج النموذج المحلي مخرجات غير صالحة لهذه اللغة، فحُذفت ولم تُعرض.",
  sourcesChoose: "اختر المصادر",
  sourcesHide: "إخفاء المصادر",
  sourcesSelected: (n, total, passages) =>
    `${n} من ${total} كتابًا · ${passages} نصًا في نطاق البحث`,
  classificationNote:
    "المذهب والمنهج مأخوذان من مرجع ثانوي وهما غير موثقين. والكتب التي لا يذكرها ذلك المرجع تُعرض بلا تصنيف بدل نسبتها إلى مذهب بالاستنتاج.",
  passagesWord: "نصًا",
  tradition: (k) =>
    ({
      EARLY: "المتقدمون",
      SUNNI: "أهل السنة",
      SUNNI_SUFI: "أهل السنة — الصوفية",
      SUNNI_SALAFI: "أهل السنة — السلفية",
      MODERNIST: "المعاصرون",
      MUTAZILA: "المعتزلة",
      TWELVER_SHIA: "الشيعة الإمامية",
      ZAYDI_SHIA: "الزيدية",
      IBADI: "الإباضية",
      UNCLASSIFIED: "قيد التصنيف",
    })[k] ?? k,
  method: (k) =>
    ({
      BI_AL_MATHUR: "بالمأثور",
      BI_AL_RAY: "بالرأي",
      FIQHI: "فقهي",
      LUGHAWI: "لغوي",
      BALAGHI: "بلاغي",
      SUFI_ISHARI: "إشاري",
      KALAMI: "كلامي",
      QIRAAT: "قراءات",
      GHARIB: "غريب",
      MIXED: "منهج مختلط",
      UNCLASSIFIED: "المنهج غير مسجل",
    })[k] ?? k,
  referencesHeading: "المراجع",
  sourcesConsulted: (n) => `${n} من المصادر المعتمدة`,
  refDied: "الوفاة",
  refEdition: "الطبعة",
  refNoPrintEdition: "نص رقمي دون طبعة مطبوعة محددة",
  refPassages: "النصوص المستشهد بها",
  refCitationDepth: "يصل التوثيق إلى",
  refToPage: "المجلد والصفحة",
  refToWork: "الكتاب فقط",
  refRights: "الحقوق",
  refVerification: "التوثيق",
  refOpenSource: "فتح سجل المصدر",
  refCoverage: (pct) =>
    `${pct}٪ من النصوص المستشهد بها تصل إلى صفحة مطبوعة. وبقيتها تصل إلى الكتاب والطبعة فقط.`,
  showTranslation: () => "النص بالعربية (المصدر)",
  hideTranslation: "إخفاء",
  translating: "جارٍ الترجمة…",
  translationInto: () => "النص الأصلي",
  machineTranslation: "ترجمة آلية",
  translationUnavailable: "لا توجد خدمة ترجمة مهيأة على الخادم. والنص العربي أعلاه هو الأصل.",
  translationFailed: "تعذّرت الترجمة. والنص العربي أعلاه لم يتأثر.",
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
  languageName: "اردو",
  originalArabic: "اصل عربی متن",
  translationPendingNote: "اس عبارت کا ترجمہ ابھی محفوظ نہیں۔ اوپر کا عربی متن اصل ہے۔",
  translationSlowNote:
    "مقامی ماڈل پر ترجمہ جاری ہے؛ ہر عبارت پر چند منٹ لگتے ہیں۔ اوپر کا عربی متن مکمل اور غیر متاثر ہے۔",
  translationRejected:
    "مقامی ماڈل نے اس زبان کے لیے ناقابلِ استعمال نتیجہ دیا، جسے دکھانے کے بجائے رد کر دیا گیا۔",
  sourcesChoose: "مآخذ منتخب کیجیے",
  sourcesHide: "مآخذ چھپائیے",
  sourcesSelected: (n, total, passages) =>
    `${total} میں سے ${n} کتابیں · ${passages} عبارات زیرِ تلاش`,
  classificationNote:
    "مسلک اور منہج ایک ثانوی مرجع سے لیے گئے ہیں اور غیر مصدقہ ہیں۔ جن کتابوں کا ذکر اس مرجع میں نہیں، انہیں قیاس سے کسی مسلک میں شامل کرنے کے بجائے غیر مصنف دکھایا گیا ہے۔",
  passagesWord: "عبارات",
  tradition: (k) =>
    ({
      EARLY: "متقدمین",
      SUNNI: "اہلِ سنت",
      SUNNI_SUFI: "اہلِ سنت — صوفیہ",
      SUNNI_SALAFI: "اہلِ سنت — سلفیہ",
      MODERNIST: "جدید",
      MUTAZILA: "معتزلہ",
      TWELVER_SHIA: "اثنا عشری شیعہ",
      ZAYDI_SHIA: "زیدی شیعہ",
      IBADI: "اباضی",
      UNCLASSIFIED: "تصنیف باقی",
    })[k] ?? k,
  method: (k) =>
    ({
      BI_AL_MATHUR: "بالمأثور",
      BI_AL_RAY: "بالرائے",
      FIQHI: "فقہی",
      LUGHAWI: "لغوی",
      BALAGHI: "بلاغی",
      SUFI_ISHARI: "اشاری",
      KALAMI: "کلامی",
      QIRAAT: "قراءات",
      GHARIB: "غریب الفاظ",
      MIXED: "مخلوط منہج",
      UNCLASSIFIED: "منہج درج نہیں",
    })[k] ?? k,
  referencesHeading: "حوالہ جات",
  sourcesConsulted: (n) => `${n} مآخذ سے استفادہ`,
  refDied: "وفات",
  refEdition: "ایڈیشن",
  refNoPrintEdition: "ڈیجیٹل متن، مطبوعہ ایڈیشن کی شناخت نہیں",
  refPassages: "پیش کردہ عبارات",
  refCitationDepth: "حوالہ کہاں تک پہنچتا ہے",
  refToPage: "جلد اور صفحہ",
  refToWork: "صرف کتاب تک",
  refRights: "حقوق",
  refVerification: "تصدیق",
  refOpenSource: "مآخذ کا ریکارڈ کھولیے",
  refCoverage: (pct) =>
    `${pct}٪ عبارات مطبوعہ صفحے تک پہنچتی ہیں۔ باقی صرف کتاب اور ایڈیشن تک۔`,
  showTranslation: (lang) => `${lang} ترجمہ دیکھیے`,
  hideTranslation: "ترجمہ چھپائیے",
  translating: "ترجمہ ہو رہا ہے…",
  translationInto: (lang) => `${lang} ترجمہ`,
  machineTranslation: "مشینی ترجمہ",
  translationUnavailable:
    "سرور پر ترجمے کی سہولت مہیا نہیں۔ اوپر کا عربی متن اصل ہے اور غیر متاثر ہے۔",
  translationFailed: "ترجمہ نہ ہو سکا۔ اوپر کا عربی متن غیر متاثر ہے۔",
};

export const COPY: Record<UiLanguage, Copy> = { en, ar, ur };
