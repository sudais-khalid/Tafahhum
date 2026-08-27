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
  readingCounts: (clauses: number, works: number) => string;
  scholarsOnThisClause: (n: number) => string;
  noSeparateTreatment: string;
  furtherDiscussion: string;
  showFullArabic: string;
  showLess: string;
  matchedByOverlap: string;
  readingTab: string;
  synthesisLabel: string;
  synthesisCaveat: string;
  synthesisNotice: string;
  buildSummary: string;
  summarising: string;
  summaryFailed: string;
  sentencesWritten: string;
  sentencesKept: string;
  sentencesRemoved: string;
  meanSupport: string;
  builtFrom: string;
  showRemoved: (n: number) => string;
  hideRemoved: string;
  evidenceTab: string;
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
  depthLabel: string;
  depthLearn: string;
  depthRead: string;
  depthAudit: string;
  depthLearnHint: string;
  depthReadHint: string;
  depthAuditHint: string;
  clausesInVerse: string;
  clauseNavHint: string;
  railSources: string;
  changeSources: string;
  jumpToClause: (n: number) => string;
  showMoreCommentators: (n: number) => string;
  auditBasis: string;
  auditConfidence: string;
  auditShowing: string;
  auditAllShown: string;
  auditHeldBack: (n: number) => string;
  basisName: (key: string) => string;
  auditGaps: string;
  auditGapsBody: string;
  showArabic: string;
  hideArabic: string;
  howItWorks: string;
  auditNoPrintEdition: string;
  verifySource: string;
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
    "Translating on the local model, this takes a few minutes per passage on CPU. The Arabic above is complete and unaffected.",
  translationRejected:
    "The local model produced unusable output for this language and it was discarded rather than shown.",
  sourcesChoose: "Choose sources",
  sourcesHide: "Hide sources",
  sourcesSelected: (n, total, passages) =>
    `${n} of ${total} works selected · ${passages.toLocaleString()} passages searched`,
  classificationNote:
    "School and method come from a tertiary reference and are unverified. Works that reference does not list are shown as unclassified rather than assigned a school by inference.",
  passagesWord: "passages",
  readingCounts: (c, w) => `${c} clauses · ${w} commentaries`,
  scholarsOnThisClause: (n) => `${n} ${n === 1 ? "commentary" : "commentaries"} on this clause`,
  noSeparateTreatment:
    "No commentary in your selection treats this clause on its own; it is discussed together with the clause beside it.",
  furtherDiscussion: "Further discussion of this ayah",
  showFullArabic: "Show the full passage",
  showLess: "Show less",
  matchedByOverlap: "matched by wording, not quoted",
  readingTab: "Read",
  synthesisLabel: "Tafahhum synthesis",
  synthesisCaveat:
    "Written by Tafahhum from the commentaries below, not by a commentator, and not a ruling.",
  synthesisNotice:
    "Every sentence was checked against the passage it cites; any that could not be traced was removed.",
  buildSummary: "Build a conclusion",
  summarising: "Reading the commentaries…",
  summaryFailed: "The conclusion could not be produced. The commentaries below are unaffected.",
  sentencesWritten: "Sentences written",
  sentencesKept: "Kept",
  sentencesRemoved: "Removed",
  meanSupport: "Mean support",
  builtFrom: "Passages used",
  showRemoved: (n) => `Show the ${n} removed sentence${n === 1 ? "" : "s"}`,
  hideRemoved: "Hide removed sentences",
  evidenceTab: "Evidence",
  tradition: (k) =>
    ({
      EARLY: "Early",
      SUNNI: "Sunni",
      SUNNI_SUFI: "Sunni, Sufi",
      SUNNI_SALAFI: "Sunni, Salafi",
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
  depthLabel: "Depth",
  depthLearn: "Learning",
  depthRead: "Reading",
  depthAudit: "Auditing",
  depthLearnHint: "Translation first, with the commentators who set out the discussion.",
  depthReadHint: "Every commentator, clause by clause, original beside translation.",
  depthAuditHint: "Adds how each passage was found, how it was matched, and how far its citation resolves.",
  clausesInVerse: "Clauses in this verse",
  clauseNavHint:
    "Numbers are how many commentators treat that clause. The divisions come from the commentaries themselves.",
  railSources: "Sources",
  changeSources: "Change",
  jumpToClause: (n) => `Go to clause ${n}`,
  showMoreCommentators: (n) =>
    `Show ${n} more ${n === 1 ? "commentator" : "commentators"} on this clause`,
  auditBasis: "Attached by",
  auditConfidence: "Confidence",
  auditShowing: "From this work",
  auditAllShown: "all shown",
  auditHeldBack: (n) => `${n} more not shown`,
  basisName: (k) =>
    ({
      QUOTED: "bracketed the clause",
      OVERLAP: "word overlap only",
      UNALIGNED: "not attached to a clause",
    })[k] ?? k,
  auditGaps: "Known gaps on this page",
  auditGapsBody:
    "Dense retrieval is not populated, so ranking rests on the structural and sparse arms only. Edition licensing is UNKNOWN for every work. No edition has page images loaded, so no citation resolves to a scan.",
  showArabic: "Show the Arabic",
  howItWorks: "How it works",
  auditNoPrintEdition:
    "Digital text of an edition the source does not identify. No volume or page is recorded, so this citation names the work, not a place in a printed book.",
  verifySource: "Source text",
  hideArabic: "Hide the Arabic",
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
  readingCounts: (c, w) => `${c} مقاطع · ${w} من التفاسير`,
  scholarsOnThisClause: (n) => `${n} من التفاسير في هذا المقطع`,
  noSeparateTreatment: "لم يفرد أحد من التفاسير المختارة هذا المقطع بالكلام، بل تُكلم عليه مع ما بجانبه.",
  furtherDiscussion: "مباحث أخرى في هذه الآية",
  showFullArabic: "إظهار النص كاملًا",
  showLess: "إظهار أقل",
  matchedByOverlap: "مطابقة بالألفاظ لا بالنص",
  readingTab: "قراءة",
  synthesisLabel: "خلاصة تفهّم",
  synthesisCaveat: "كتبها تفهّم من التفاسير أدناه، لا مفسّر، وليست فتوى.",
  synthesisNotice: "قوبلت كل جملة بالنص الذي تحيل إليه، وحُذف ما لم يمكن ردّه إليه.",
  buildSummary: "استخراج خلاصة",
  summarising: "قراءة التفاسير…",
  summaryFailed: "تعذّر إنتاج الخلاصة. والتفاسير أدناه لم تتأثر.",
  sentencesWritten: "الجمل المكتوبة",
  sentencesKept: "المُبقاة",
  sentencesRemoved: "المحذوفة",
  meanSupport: "متوسط الإسناد",
  builtFrom: "النصوص المعتمدة",
  showRemoved: (n) => `إظهار ${n} من الجمل المحذوفة`,
  hideRemoved: "إخفاء المحذوفة",
  evidenceTab: "الشواهد",
  tradition: (k) =>
    ({
      EARLY: "المتقدمون",
      SUNNI: "أهل السنة",
      SUNNI_SUFI: "أهل السنة, الصوفية",
      SUNNI_SALAFI: "أهل السنة, السلفية",
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
  depthLabel: "المستوى",
  depthLearn: "تعلّم",
  depthRead: "قراءة",
  depthAudit: "تدقيق",
  depthLearnHint: "الترجمة أولاً، مع المفسّرين الذين يقيمون أصل المسألة.",
  depthReadHint: "كل المفسّرين، جملةً جملةً، مع النص الأصلي إلى جانب الترجمة.",
  depthAuditHint: "يضيف كيف عُثر على كل نص، وكيف رُبط بالجملة، وإلى أي حدّ يصل توثيقه.",
  clausesInVerse: "جمل هذه الآية",
  clauseNavHint: "الأرقام تدل على عدد المفسّرين الذين تناولوا الجملة. والتقسيم مأخوذ من التفاسير نفسها.",
  railSources: "المصادر",
  changeSources: "تغيير",
  jumpToClause: (n) => `الانتقال إلى الجملة ${n}`,
  showMoreCommentators: (n) => `إظهار ${n} من التفاسير الأخرى في هذا المقطع`,
  auditBasis: "أُلحق بـ",
  auditConfidence: "درجة الثقة",
  auditShowing: "من هذا الكتاب",
  auditAllShown: "الكل معروض",
  auditHeldBack: (n) => `${n} غير معروضة`,
  basisName: (k) =>
    ({
      QUOTED: "وضع المقطع بين قوسين",
      OVERLAP: "تشابه لفظي فقط",
      UNALIGNED: "غير ملحق بمقطع",
    })[k] ?? k,
  auditGaps: "ثغرات معلومة في هذه الصفحة",
  auditGapsBody:
    "البحث الدلالي غير مفعّل، فالترتيب يعتمد على البنية والمطابقة اللفظية فقط. وحالة الحقوق لكل طبعة غير معروفة. ولا توجد صور للصفحات، فلا يصل أي توثيق إلى المصوّرة.",
  showArabic: "إظهار النص العربي",
  howItWorks: "كيف يعمل",
  auditNoPrintEdition:
    "نص رقمي لطبعة لا يحددها المصدر. ولم يُسجَّل جزء ولا صفحة، فهذا التوثيق يسمّي الكتاب لا موضعاً في مطبوع.",
  verifySource: "النص المصدر",
  hideArabic: "إخفاء النص العربي",
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
  readingCounts: (c, w) => `${c} اجزا · ${w} تفاسیر`,
  scholarsOnThisClause: (n) => `اس جزو پر ${n} تفاسیر`,
  noSeparateTreatment:
    "منتخب تفاسیر میں سے کسی نے اس جزو پر الگ کلام نہیں کیا؛ اسے ساتھ والے جزو کے ساتھ بیان کیا گیا ہے۔",
  furtherDiscussion: "اس آیت پر مزید مباحث",
  showFullArabic: "مکمل عبارت دکھائیے",
  showLess: "کم دکھائیے",
  matchedByOverlap: "الفاظ سے مطابقت، اقتباس سے نہیں",
  readingTab: "مطالعہ",
  synthesisLabel: "تفہّم کی خلاصہ",
  synthesisCaveat: "یہ تفہّم نے نیچے دی گئی تفاسیر سے لکھی ہے؛ کسی مفسر کا کلام نہیں، اور فتویٰ نہیں۔",
  synthesisNotice: "ہر جملہ اس عبارت سے جانچا گیا جس کا حوالہ دیا گیا؛ جو نہ جچ سکا وہ حذف کر دیا گیا۔",
  buildSummary: "خلاصہ نکالیے",
  summarising: "تفاسیر پڑھی جا رہی ہیں…",
  summaryFailed: "خلاصہ تیار نہ ہو سکا۔ نیچے کی تفاسیر غیر متاثر ہیں۔",
  sentencesWritten: "لکھے گئے جملے",
  sentencesKept: "رکھے گئے",
  sentencesRemoved: "حذف شدہ",
  meanSupport: "اوسط سند",
  builtFrom: "استعمال شدہ عبارات",
  showRemoved: (n) => `${n} حذف شدہ جملے دیکھیے`,
  hideRemoved: "حذف شدہ چھپائیے",
  evidenceTab: "شواہد",
  tradition: (k) =>
    ({
      EARLY: "متقدمین",
      SUNNI: "اہلِ سنت",
      SUNNI_SUFI: "اہلِ سنت, صوفیہ",
      SUNNI_SALAFI: "اہلِ سنت, سلفیہ",
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
  depthLabel: "سطح",
  depthLearn: "سیکھنا",
  depthRead: "مطالعہ",
  depthAudit: "جانچ",
  depthLearnHint: "پہلے ترجمہ، اور وہ مفسرین جو بحث کی بنیاد رکھتے ہیں۔",
  depthReadHint: "تمام مفسرین، جملہ بہ جملہ، اصل متن ترجمے کے ساتھ۔",
  depthAuditHint: "بتاتا ہے کہ ہر اقتباس کیسے ملا، کیسے جوڑا گیا، اور اس کا حوالہ کہاں تک پہنچتا ہے۔",
  clausesInVerse: "اس آیت کے اجزا",
  clauseNavHint: "اعداد بتاتے ہیں کہ کتنے مفسرین نے اس جزو پر بات کی۔ یہ تقسیم خود تفاسیر سے لی گئی ہے۔",
  railSources: "مآخذ",
  changeSources: "تبدیل کریں",
  jumpToClause: (n) => `جزو ${n} پر جائیں`,
  showMoreCommentators: (n) => `اس جزو پر ${n} مزید تفاسیر دیکھیں`,
  auditBasis: "منسلک بذریعہ",
  auditConfidence: "درجہ اعتماد",
  auditShowing: "اس کتاب سے",
  auditAllShown: "سب دکھائے گئے",
  auditHeldBack: (n) => `${n} مزید نہیں دکھائے گئے`,
  basisName: (k) =>
    ({
      QUOTED: "جزو کو قوسین میں لکھا",
      OVERLAP: "صرف لفظی مشابہت",
      UNALIGNED: "کسی جزو سے منسلک نہیں",
    })[k] ?? k,
  auditGaps: "اس صفحے کی معلوم کمیاں",
  auditGapsBody:
    "معنوی تلاش فعال نہیں، اس لیے ترتیب صرف ساختی اور لفظی بنیاد پر ہے۔ ہر کتاب کے حقوق کی حیثیت نامعلوم ہے۔ کسی طبع کے صفحات کی تصاویر موجود نہیں، اس لیے کوئی حوالہ اصل صفحے تک نہیں پہنچتا۔",
  showArabic: "عربی متن دکھائیں",
  howItWorks: "یہ کیسے کام کرتا ہے",
  auditNoPrintEdition:
    "ایک ایسی طبع کا برقی متن جس کی نشاندہی ماخذ نہیں کرتا۔ جلد اور صفحہ درج نہیں، اس لیے یہ حوالہ کتاب کا نام دیتا ہے، کسی مطبوعہ مقام کا نہیں۔",
  verifySource: "ماخذ متن",
  hideArabic: "عربی متن چھپائیں",
};

export const COPY: Record<UiLanguage, Copy> = { en, ar, ur };
