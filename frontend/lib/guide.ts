import type { UiLanguage } from "./types";

/* The "How it works" content, in the three user languages.
 *
 * Kept out of i18n.ts because it is prose rather than interface labels, and
 * because it is long enough to bury everything else in that file.
 *
 * One rule governs what may be written here: this page may only claim things
 * the system actually does. Where a limit exists it is stated on this page
 * rather than left for a reader to discover, because a page arguing for trust
 * that omits the known gaps is arguing dishonestly.
 */

export interface GuideControl {
  /** What the reader sees on screen. */
  name: string;
  /** Where they see it. */
  where: string;
  /** What it does, and why it behaves the way it does. */
  detail: string;
}

export interface GuideSection {
  id: string;
  title: string;
  body: string[];
  controls?: GuideControl[];
}

export interface Guide {
  title: string;
  standfirst: string;
  back: string;
  chainTitle: string;
  chainNote: string;
  chain: { step: string; label: string; detail: string }[];
  sections: GuideSection[];
  neverTitle: string;
  neverNote: string;
  never: string[];
  gapsTitle: string;
  gapsNote: string;
  gaps: { name: string; detail: string }[];
  checkTitle: string;
  check: string[];
  contactTitle: string;
  contactBody: string;
  contactCorrections: string;
  contactEmail: string;
  contactWhatsapp: string;
  contactSite: string;
  ownership: string;
}

const en: Guide = {
  title: "How Tafahhum works",
  standfirst:
    "Tafahhum organises and cites the Tafsir tradition. It does not write Tafsir. This page explains what every control on the site does, where the text on your screen came from, and what this system cannot currently do.",
  back: "Back to search",

  chainTitle: "The chain every answer follows",
  chainNote:
    "The order matters and is never reversed. Nothing is written before the sources are found, and nothing is shown before it is checked against them.",
  chain: [
    {
      step: "1",
      label: "Source",
      detail:
        "A commentary is ingested from an identified work and stored with the edition it came from. The original text is written once and can never be edited afterwards, which the database enforces rather than trusting the code to remember.",
    },
    {
      step: "2",
      label: "Structure",
      detail:
        "Each passage is attached to the verses it discusses, and to the specific clause within a verse where the commentator brackets one. The clause divisions are taken from the commentaries themselves, not decided by us.",
    },
    {
      step: "3",
      label: "Retrieve",
      detail:
        "Your question is resolved to a verse, then passages are found three ways at once: by verse range, by wording, and by meaning. The results are combined by rank rather than score, and capped per work so that a long commentary cannot crowd out a short one.",
    },
    {
      step: "4",
      label: "Verify",
      detail:
        "Anything written by Tafahhum is checked sentence by sentence against the passage it claims to draw on. A sentence that cannot be traced is deleted before you ever see it, and the count of deletions is shown to you.",
    },
    {
      step: "5",
      label: "Synthesise",
      detail:
        "Only what survived verification is assembled into a summary, and it is marked as written by Tafahhum so it can never be mistaken for a commentator's words.",
    },
    {
      step: "6",
      label: "Cite",
      detail:
        "Every passage carries the work and author it came from, a link to the exact source file it was ingested from, and a ladder showing how far that citation actually resolves. Volume and page are not recorded for any work in the corpus, and the ladder shows that rather than hiding it.",
    },
  ],

  sections: [
    {
      id: "reading",
      title: "The search bar and the reading page",
      body: [
        "Type a question in ordinary language. You do not need to know a verse number: 'what does the throne verse say about God being free of sleep' resolves to 2:255, and the Auditing depth will show you how it did so.",
        "When a question resolves to a single verse you get the reading page, which takes the verse apart clause by clause and shows what each commentator said about each clause. When it resolves to several, you get the evidence view instead, which is a flat list better suited to comparison.",
      ],
      controls: [
        {
          name: "Search",
          where: "Top of the page",
          detail:
            "Accepts English, Arabic and Urdu. Whatever you type, the actual search runs in Arabic, because the commentaries are in Arabic and translating them to match your query would mean searching a translation rather than a source.",
        },
        {
          name: "The verse panel",
          where: "Left side of the reading page",
          detail:
            "The verse and one published translation, held in place while the commentary beside it scrolls. It is the only element on the site allowed to use gold, so you can always tell revealed text from commentary at a glance without reading a label.",
        },
        {
          name: "Clauses in this verse",
          where: "Left panel, below the verse",
          detail:
            "Every clause the commentators treat separately, with the number of commentators who treat it. Click one to jump to it. A clause nobody treats on its own is folded into its neighbour rather than shown as an empty heading, because an empty heading would suggest the tradition passed over it in silence.",
        },
      ],
    },
    {
      id: "depth",
      title: "The depth dial",
      body: [
        "One control changes how much of the machinery is drawn around the evidence. It does not change which sources are searched, and it never removes a commentator without telling you. Your choice is remembered on your own device.",
      ],
      controls: [
        {
          name: "Learning",
          where: "Masthead",
          detail:
            "The translation leads and opens by itself, because at this depth the translation is what you came for. The Arabic folds behind a control and is always one click away. Two commentators lead each clause and the rest sit behind a button that says exactly how many are waiting.",
        },
        {
          name: "Reading",
          where: "Masthead",
          detail:
            "The default. Every commentator on every clause, the Arabic first with the translation on request. This is the honest default because Learning hides commentators and Auditing shows machinery most readers never asked for.",
        },
        {
          name: "Auditing",
          where: "Masthead",
          detail:
            "Adds a record under each passage: how far its citation resolves, what attached it to the clause and how confidently, and how many further passages that work has on the same clause. It also states the corpus-wide gaps at the top of the page.",
        },
      ],
    },
    {
      id: "sources",
      title: "Choosing sources",
      body: [
        "You decide which works are searched. The list carries each work's school and method where a reference records them, and marks the rest as unclassified rather than guessing.",
      ],
      controls: [
        {
          name: "Sources",
          where: "Below the search bar",
          detail:
            "Presets and individual works. The count tells you how many passages your current selection actually searches, so a narrow selection cannot silently look like a complete one.",
        },
        {
          name: "School and method labels",
          where: "In the source list",
          detail:
            "Taken from a tertiary reference and not independently verified, which is why they are labelled as such. A work the reference does not list is shown as unclassified rather than assigned a school by inference.",
        },
      ],
    },
    {
      id: "passages",
      title: "Reading a passage",
      body: [
        "Every commentary card is quoted text. Nothing in a card is written by Tafahhum, and the Arabic is always present even when a translation is shown above it.",
      ],
      controls: [
        {
          name: "Show the full passage",
          where: "On each commentary card",
          detail:
            "Cards show an opening extract by default. This opens the complete passage as stored, unedited.",
        },
        {
          name: "Translate into your language",
          where: "On each commentary card",
          detail:
            "Produces a machine translation, always labelled as one. It never replaces the Arabic, and where part of a passage could not be translated the card says how many sentences are missing rather than presenting a shortened translation as the whole.",
        },
        {
          name: "Matched by wording, not quoted",
          where: "On some cards, at Reading and Auditing depth",
          detail:
            "A warning. This passage was attached to the clause because its words overlap, not because the commentator bracketed the clause. That is a weaker claim and it is marked so you can weigh it differently.",
        },
      ],
    },
    {
      id: "conclusion",
      title: "The conclusion, and why you can check it",
      body: [
        "The conclusion is the only text on the site written by Tafahhum rather than quoted. It is drawn in a different colour and labelled, so it can never be mistaken for a commentator.",
        "It is written from the passages shown below it and nothing else. The model is given the passages with no author names, no work titles and no dates, so it cannot reach for what it already knows about al-Tabari and write that instead of what the passage in front of it says.",
        "Every sentence is then measured against the passage it cites. A sentence whose wording is not supported by that passage is deleted. So is one that merely recites the verse, and one that copies a passage word for word instead of summarising it.",
      ],
      controls: [
        {
          name: "Sentences written, Kept, Removed",
          where: "Under the conclusion",
          detail:
            "The filter's own record. A conclusion that discarded three sentences is more trustworthy than one claiming it discarded none, so the numbers are shown rather than hidden.",
        },
        {
          name: "Mean support",
          where: "Under the conclusion",
          detail:
            "How strongly, on average, the surviving sentences are grounded in the passages they cite. It is a measurement you could recompute yourself, not a confidence score the model reported about itself.",
        },
        {
          name: "Show the removed sentences",
          where: "Under the conclusion",
          detail:
            "What was cut, and why. Showing you the rejects is the point: it is the evidence that the filter runs at all.",
        },
      ],
    },
    {
      id: "citations",
      title: "Citations and the provenance ladder",
      body: [
        "Every passage is numbered and the numbers match the reference list at the bottom of the page.",
        "The ladder runs Work, Edition, Volume, Page, Scan. A filled dot means that step resolves. A hollow dot means it does not exist in the corpus, and it is drawn rather than omitted so a limitation cannot be missed by someone skimming. At present only the first step is filled for every passage, because the print edition behind the digital text is not identified.",
      ],
      controls: [
        {
          name: "The reference list",
          where: "Bottom of the reading page",
          detail:
            "Author, work, edition and page for every source that contributed, in the order they first appear.",
        },
        {
          name: "How this answer was built",
          where: "Auditing depth",
          detail:
            "The retrieval trace: what your question was taken to mean, the Arabic terms actually searched, which methods found what, and which rules were applied.",
        },
      ],
    },
  ],

  neverTitle: "What Tafahhum will not do",
  neverNote:
    "These are enforced by the system rather than left to good intentions. Several are database constraints, which means the data cannot be stored in a form that breaks them.",
  never: [
    "Invent a citation, a page number, a quotation, or a Mufassir.",
    "Present a translation as though it were the source text.",
    "Claim scholarly consensus that its sources do not state.",
    "Store a rule that claims scholarly authority without recording where that authority comes from.",
    "Edit a passage after it has been ingested. The original text is immutable and the database enforces it.",
    "Show a written sentence that could not be traced to a passage.",
    "Issue a legal ruling, or tell you what to believe.",
  ],

  gapsTitle: "What is not finished",
  gapsNote:
    "A page arguing that you should trust this system would be dishonest if it left these out.",
  gaps: [
    {
      name: "Citations name the work, not a page in it",
      detail:
        "This is the most important limit on this page. The text comes from a digital aggregation that does not identify the underlying print edition, so no passage in the corpus carries a volume or page number, and none has a page image. A citation here tells you which commentator said something and lets you fetch the exact source file we ingested, but it will not take you to a place in a printed book. Checking a passage against a specific tahqiq remains your work, not ours.",
    },
    {
      name: "Edition licensing is unknown",
      detail:
        "The text comes from an open aggregation that does not identify the underlying print edition, so the copyright status of every edition is recorded as UNKNOWN rather than assumed to be clear.",
    },
    {
      name: "Meaning-based search is not populated",
      detail:
        "Ranking currently rests on verse structure and wording. The third method exists but has no data behind it yet, so a passage that discusses your question in different words may not surface.",
    },
    {
      name: "Translations are machine-made",
      detail:
        "No translation on this site has been checked by a human translator. They are labelled as machine translations everywhere they appear, and the Arabic is always shown beside them.",
    },
    {
      name: "Coverage is partial",
      detail:
        "The corpus grows work by work. If a commentator does not appear on a verse, that may mean the work is not fully ingested rather than that the commentator was silent. Absence here is not evidence of silence.",
    },
  ],

  checkTitle: "How to check us",
  check: [
    "Switch to Auditing depth and read the trace: it shows what your question was taken to mean before anything was retrieved.",
    "Open any conclusion's removed sentences. If nothing is ever removed, the filter is not working.",
    "Take a citation to the printed edition. The volume and page are there for exactly that.",
    "Compare the translation against the Arabic beside it. They are shown together for this reason.",
    "Narrow your sources to one work and see whether the conclusion changes. It should.",
  ],
  contactTitle: "Contact, corrections and collaboration",
  contactBody:
    "Tafahhum is built and maintained by Sudais Khalid. If you find a mistake, a misattribution, a bad translation, or a passage credited to the wrong commentator, please report it. Corrections from people who know this material are the fastest way this becomes reliable, and they are welcome without reservation.",
  contactCorrections:
    "Suggestions and collaboration are equally welcome, particularly from scholars who can identify the print editions behind these texts, which is the single largest gap listed above.",
  contactEmail: "Email",
  contactWhatsapp: "WhatsApp",
  contactSite: "Website",
  ownership: "Tafahhum is the work of Sudais Khalid.",
};

const ar: Guide = {
  title: "كيف يعمل تفهُّم",
  standfirst:
    "تفهُّم ينظّم تراث التفسير ويوثّقه، ولا يكتب تفسيراً. تشرح هذه الصفحة وظيفة كل أداة في الموقع، ومصدر كل نص تراه، وما لا يستطيع هذا النظام فعله حتى الآن.",
  back: "العودة إلى البحث",

  chainTitle: "السلسلة التي يتبعها كل جواب",
  chainNote: "الترتيب مقصود ولا يُعكس أبداً. لا يُكتب شيء قبل العثور على المصادر، ولا يُعرض شيء قبل مقابلته بها.",
  chain: [
    {
      step: "١",
      label: "المصدر",
      detail:
        "يُدخل التفسير من كتاب محدد ويُحفظ مع الطبعة التي جاء منها. ويُكتب النص الأصلي مرة واحدة ولا يمكن تعديله بعدها، وقاعدة البيانات هي التي تفرض ذلك لا الاعتماد على انضباط البرمجة.",
    },
    {
      step: "٢",
      label: "البنية",
      detail:
        "يُربط كل نص بالآيات التي يتناولها، وبالمقطع المعيّن داخل الآية حين يضعه المفسّر بين قوسين. وتقسيم المقاطع مأخوذ من التفاسير نفسها لا من عندنا.",
    },
    {
      step: "٣",
      label: "الاسترجاع",
      detail:
        "يُردّ سؤالك إلى آية، ثم تُطلب النصوص بثلاث طرق معاً: بنطاق الآية، وباللفظ، وبالمعنى. وتُدمج النتائج بالرتبة لا بالدرجة، ويُحدّ نصيب كل كتاب حتى لا يزحم تفسيرٌ مطوَّل تفسيراً موجزاً.",
    },
    {
      step: "٤",
      label: "التحقق",
      detail:
        "كل ما يكتبه تفهُّم يُقابَل جملةً جملةً بالنص الذي يدّعي الاستناد إليه. والجملة التي لا يمكن ردّها إلى مصدرها تُحذف قبل أن تراها، ويُعرض عليك عدد المحذوف.",
    },
    {
      step: "٥",
      label: "التركيب",
      detail:
        "لا يُجمع في الخلاصة إلا ما نجا من التحقق، وتُعلَّم بأنها من كتابة تفهُّم حتى لا تُشتبه بكلام مفسّر.",
    },
    {
      step: "٦",
      label: "التوثيق",
      detail:
        "كل نص يحمل الكتاب والمؤلف، ورابطاً إلى الملف المصدر الذي أُدخل منه بعينه، مع سُلّم يبيّن إلى أي حدّ يصل هذا التوثيق فعلاً. ولا يُسجَّل جزء ولا صفحة لأي كتاب في المدوّنة، والسُّلّم يُظهر ذلك ولا يخفيه.",
    },
  ],

  sections: [
    {
      id: "reading",
      title: "شريط البحث وصفحة القراءة",
      body: [
        "اكتب سؤالك بلغة عادية. لا يلزمك معرفة رقم الآية: سؤال عن آية الكرسي والنوم يُردّ إلى ٢:٢٥٥، ومستوى التدقيق يريك كيف تم ذلك.",
        "إذا انتهى السؤال إلى آية واحدة ظهرت صفحة القراءة، وهي تفكك الآية مقطعاً مقطعاً وتعرض ما قاله كل مفسّر في كل مقطع. وإذا انتهى إلى عدة آيات ظهرت صفحة الأدلة، وهي قائمة مسطّحة أنسب للمقارنة.",
      ],
      controls: [
        {
          name: "البحث",
          where: "أعلى الصفحة",
          detail:
            "يقبل العربية والإنجليزية والأردية. وأياً كان ما تكتبه فالبحث يجري بالعربية، لأن التفاسير عربية، ولو تُرجمت لمطابقة سؤالك لكان البحث في ترجمة لا في مصدر.",
        },
        {
          name: "لوحة الآية",
          where: "جانب صفحة القراءة",
          detail:
            "الآية وترجمة منشورة واحدة، تبقى ثابتة بينما ينساب التفسير بجوارها. وهي العنصر الوحيد في الموقع المسموح له باللون الذهبي، فيتميز النص المنزّل عن التفسير بالنظر لا بقراءة تسمية.",
        },
        {
          name: "مقاطع هذه الآية",
          where: "اللوحة الجانبية أسفل الآية",
          detail:
            "كل مقطع أفرده المفسّرون بالكلام، ومعه عدد من تكلم فيه. انقر عليه للانتقال إليه. والمقطع الذي لم يُفرَد يُضمّ إلى جاره بدل عرضه عنواناً فارغاً، لأن العنوان الفارغ يوهم أن التراث سكت عنه.",
        },
      ],
    },
    {
      id: "depth",
      title: "مِفتاح المستوى",
      body: [
        "أداة واحدة تغيّر مقدار ما يُرسم من الأجهزة حول الدليل. ولا تغيّر المصادر التي يُبحث فيها، ولا تحذف مفسّراً دون إخبارك. واختيارك محفوظ على جهازك أنت.",
      ],
      controls: [
        {
          name: "تعلّم",
          where: "الشريط العلوي",
          detail:
            "تتصدّر الترجمة وتُفتح من تلقاء نفسها، لأنها في هذا المستوى هي المقصودة. ويُطوى النص العربي خلف زر ويبقى على بعد نقرة واحدة دائماً. ويتصدّر كل مقطعٍ مفسّران، والبقية خلف زر يذكر عددهم بالضبط.",
        },
        {
          name: "قراءة",
          where: "الشريط العلوي",
          detail:
            "المستوى الافتراضي. كل المفسّرين على كل مقطع، والعربية أولاً والترجمة عند الطلب. وهو الافتراض الأمين لأن التعلّم يخفي مفسّرين، والتدقيق يعرض أجهزة لم يطلبها أكثر القراء.",
        },
        {
          name: "تدقيق",
          where: "الشريط العلوي",
          detail:
            "يضيف تحت كل نص سجلاً: إلى أي حدّ يصل توثيقه، وبأي شيء أُلحق بالمقطع وبأي درجة ثقة، وكم بقي لذلك الكتاب من نصوص على المقطع نفسه. ويذكر أيضاً ثغرات المدوّنة في أعلى الصفحة.",
        },
      ],
    },
    {
      id: "sources",
      title: "اختيار المصادر",
      body: [
        "أنت من يقرر أي الكتب يُبحث فيها. وتحمل القائمة مذهب كل كتاب ومنهجه حيث يذكرهما مرجع، وتُبقي الباقي غير مصنّف بدل التخمين.",
      ],
      controls: [
        {
          name: "المصادر",
          where: "أسفل شريط البحث",
          detail:
            "مجموعات جاهزة وكتب مفردة. والعدد يخبرك بكم نصاً يبحث فيه اختيارك الحالي فعلاً، حتى لا يبدو الاختيار الضيّق وكأنه شامل.",
        },
        {
          name: "تسميات المذهب والمنهج",
          where: "في قائمة المصادر",
          detail:
            "مأخوذة من مرجع ثانوي ولم تُتحقق استقلالاً، ولهذا تُعلَّم بذلك. والكتاب الذي لا يذكره المرجع يُعرض غير مصنّف بدل نسبته إلى مذهب بالاستنتاج.",
        },
      ],
    },
    {
      id: "passages",
      title: "قراءة النص",
      body: [
        "كل بطاقة تفسير نصٌّ منقول. ولا شيء فيها من كتابة تفهُّم، والعربية حاضرة دائماً حتى مع عرض الترجمة فوقها.",
      ],
      controls: [
        {
          name: "إظهار النص كاملاً",
          where: "على كل بطاقة",
          detail: "تعرض البطاقات مقتطفاً افتتاحياً افتراضاً. وهذا يفتح النص كاملاً كما حُفظ دون تعديل.",
        },
        {
          name: "الترجمة إلى لغتك",
          where: "على كل بطاقة",
          detail:
            "تنتج ترجمة آلية، وتُعلَّم بذلك دائماً. ولا تحلّ محل العربية أبداً، وإذا تعذّرت ترجمة جزء من النص ذكرت البطاقة عدد الجمل الناقصة بدل تقديم ترجمة مبتورة على أنها تامة.",
        },
        {
          name: "تشابه لفظي لا اقتباس",
          where: "على بعض البطاقات في مستويي القراءة والتدقيق",
          detail:
            "تنبيه. أُلحق هذا النص بالمقطع لتشابه ألفاظه لا لأن المفسّر وضع المقطع بين قوسين. وهي دعوى أضعف، وتُعلَّم لتزنها وزناً مختلفاً.",
        },
      ],
    },
    {
      id: "conclusion",
      title: "الخلاصة، ولماذا يمكنك التحقق منها",
      body: [
        "الخلاصة هي النص الوحيد في الموقع من كتابة تفهُّم لا من النقل. وتُرسم بلون مختلف وتُعلَّم، فلا تُشتبه بمفسّر أبداً.",
        "وتُكتب من النصوص المعروضة تحتها لا غير. ويُعطى النموذج النصوص بلا أسماء مؤلفين ولا عناوين كتب ولا تواريخ، حتى لا يستدعي ما يعرفه سلفاً عن الطبري فيكتبه بدل ما يقوله النص أمامه.",
        "ثم تُقاس كل جملة بالنص الذي تحيل إليه. فتُحذف الجملة التي لا يسندها ذلك النص، وكذلك التي تكتفي بترديد الآية، والتي تنسخ النص حرفاً بحرف بدل تلخيصه.",
      ],
      controls: [
        {
          name: "الجمل المكتوبة والمبقاة والمحذوفة",
          where: "تحت الخلاصة",
          detail:
            "سجل المصفاة نفسها. فالخلاصة التي حذفت ثلاث جمل أجدر بالثقة من التي تدّعي أنها لم تحذف شيئاً، ولهذا تُعرض الأرقام ولا تُخفى.",
        },
        {
          name: "متوسط الإسناد",
          where: "تحت الخلاصة",
          detail:
            "مقدار استناد الجمل الباقية إلى نصوصها في المتوسط. وهو قياس تستطيع إعادة حسابه بنفسك، لا درجة ثقة أفاد بها النموذج عن نفسه.",
        },
        {
          name: "إظهار الجمل المحذوفة",
          where: "تحت الخلاصة",
          detail: "ما حُذف ولماذا. وعرض المرفوض هو المقصود: فهو الدليل على أن المصفاة تعمل أصلاً.",
        },
      ],
    },
    {
      id: "citations",
      title: "التوثيق وسُلّم الإسناد",
      body: [
        "كل نص مرقّم، والأرقام تطابق قائمة المراجع في أسفل الصفحة.",
        "ويمضي السُّلّم: الكتاب، الطبعة، الجزء، الصفحة، المصوّرة. والنقطة الممتلئة تعني أن هذه الدرجة متحققة، والفارغة تعني أنها غير موجودة في المدوّنة، وتُرسم ولا تُحذف حتى لا يفوت النقصُ من يقرأ سريعاً. وفي الحال الراهنة لا تمتلئ إلا الدرجة الأولى في كل نص، لأن الطبعة المطبوعة وراء النص الرقمي غير محددة.",
      ],
      controls: [
        {
          name: "قائمة المراجع",
          where: "أسفل صفحة القراءة",
          detail: "المؤلف والكتاب والطبعة والصفحة لكل مصدر أسهم، بترتيب أول ظهورها.",
        },
        {
          name: "كيف بُني هذا الجواب",
          where: "مستوى التدقيق",
          detail:
            "أثر الاسترجاع: كيف فُهم سؤالك، والألفاظ العربية التي بُحث بها فعلاً، وأي الطرق وجدت ماذا، وأي القواعد طُبّقت.",
        },
      ],
    },
  ],

  neverTitle: "ما لا يفعله تفهُّم",
  neverNote:
    "هذه مفروضة بالنظام لا موكولة إلى حسن النية. وعدد منها قيود في قاعدة البيانات، بمعنى أن البيانات لا يمكن أن تُحفظ أصلاً على صورة تخالفها.",
  never: [
    "اختلاق توثيق أو رقم صفحة أو نقل أو اسم مفسّر.",
    "تقديم ترجمة على أنها النص الأصلي.",
    "دعوى إجماع لا تذكره مصادره.",
    "حفظ قاعدة تدّعي حجية شرعية دون تسجيل مصدر تلك الحجية.",
    "تعديل نص بعد إدخاله. فالنص الأصلي غير قابل للتغيير وقاعدة البيانات تفرض ذلك.",
    "عرض جملة مكتوبة تعذّر ردّها إلى نص.",
    "إصدار حكم شرعي أو إملاء ما ينبغي أن تعتقده.",
  ],

  gapsTitle: "ما لم يكتمل بعد",
  gapsNote: "صفحة تدعوك إلى الثقة بهذا النظام تكون غير أمينة لو أغفلت هذه.",
  gaps: [
    {
      name: "التوثيق يسمّي الكتاب لا موضعاً فيه",
      detail:
        "هذا أهم قيد في هذه الصفحة. النص مأخوذ من تجميع رقمي لا يحدد الطبعة المطبوعة الأصلية، فلا يحمل أي نص في المدوّنة جزءاً ولا صفحة، ولا توجد صورة صفحة. فالتوثيق هنا يخبرك بمن قال، ويتيح لك جلب الملف المصدر بعينه، لكنه لا يوصلك إلى موضع في مطبوع. ومقابلة النص بتحقيق معيّن تبقى من عملك أنت لا من عملنا.",
    },
    {
      name: "حقوق الطبعات غير معروفة",
      detail:
        "النص من تجميع مفتوح لا يحدد الطبعة المطبوعة الأصلية، فحالة الحقوق لكل طبعة مسجَّلة بأنها غير معروفة بدل افتراض خلوّها.",
    },
    {
      name: "البحث بالمعنى غير مفعّل",
      detail:
        "الترتيب الآن قائم على بنية الآية واللفظ. والطريقة الثالثة موجودة لكن لا بيانات وراءها بعد، فقد لا يظهر نص يعالج سؤالك بألفاظ أخرى.",
    },
    {
      name: "الترجمات آلية",
      detail:
        "لا ترجمة في هذا الموقع راجعها مترجم بشري. وتُعلَّم بأنها آلية حيثما ظهرت، والعربية معروضة بجوارها دائماً.",
    },
    {
      name: "التغطية جزئية",
      detail:
        "تنمو المدوّنة كتاباً كتاباً. فإن لم يظهر مفسّر على آية فقد يعني ذلك أن كتابه لم يكتمل إدخاله لا أنه سكت. وغياب المصدر هنا ليس دليلاً على سكوته.",
    },
  ],

  checkTitle: "كيف تتحقق منّا",
  check: [
    "انتقل إلى مستوى التدقيق واقرأ الأثر: يبيّن كيف فُهم سؤالك قبل استرجاع أي شيء.",
    "افتح الجمل المحذوفة من أي خلاصة. فإن لم يُحذف شيء أبداً فالمصفاة لا تعمل.",
    "خذ توثيقاً إلى الطبعة المطبوعة. الجزء والصفحة موضوعان لهذا بعينه.",
    "قابل الترجمة بالعربية التي بجوارها. وهما معروضتان معاً لهذا السبب.",
    "ضيّق مصادرك إلى كتاب واحد وانظر هل تتغير الخلاصة. ينبغي أن تتغير.",
  ],
  contactTitle: "التواصل والتصويب والتعاون",
  contactBody:
    "تفهُّم من بناء سُديس خالد وصيانته. فإن وجدت خطأً أو نسبةً غير صحيحة أو ترجمةً رديئة أو نصاً نُسب إلى غير قائله، فأرجو إبلاغي. فتصويبات أهل العلم بهذه المادة أسرع طريق إلى أن يصير هذا العمل موثوقاً، وهي مرحّب بها بلا تحفظ.",
  contactCorrections:
    "والاقتراحات والتعاون مرحّب بهما كذلك، ولا سيما من العلماء الذين يستطيعون تحديد الطبعات المطبوعة وراء هذه النصوص، وهي أكبر ثغرة ذُكرت أعلاه.",
  contactEmail: "البريد",
  contactWhatsapp: "واتساب",
  contactSite: "الموقع",
  ownership: "تفهُّم من عمل سُديس خالد.",
};

const ur: Guide = {
  title: "تفہُّم کیسے کام کرتا ہے",
  standfirst:
    "تفہُّم تفسیری روایت کو مرتب کرتا اور اس کا حوالہ دیتا ہے، تفسیر لکھتا نہیں۔ یہ صفحہ بتاتا ہے کہ سائٹ کا ہر بٹن کیا کرتا ہے، آپ کی سکرین کا متن کہاں سے آیا، اور یہ نظام فی الحال کیا نہیں کر سکتا۔",
  back: "تلاش پر واپس",

  chainTitle: "ہر جواب جس سلسلے سے گزرتا ہے",
  chainNote:
    "ترتیب بامقصد ہے اور کبھی الٹی نہیں ہوتی۔ مآخذ ملنے سے پہلے کچھ نہیں لکھا جاتا، اور ان سے ملائے بغیر کچھ نہیں دکھایا جاتا۔",
  chain: [
    {
      step: "۱",
      label: "ماخذ",
      detail:
        "تفسیر ایک متعین کتاب سے لی جاتی ہے اور اسی طبع کے ساتھ محفوظ ہوتی ہے۔ اصل متن ایک بار لکھا جاتا ہے اور بعد میں بدلا نہیں جا سکتا، اور یہ پابندی ڈیٹابیس خود لگاتا ہے۔",
    },
    {
      step: "۲",
      label: "ساخت",
      detail:
        "ہر اقتباس ان آیات سے جوڑا جاتا ہے جن پر وہ بحث کرتا ہے، اور آیت کے اس مخصوص جزو سے بھی جہاں مفسر اسے قوسین میں لکھتا ہے۔ اجزا کی تقسیم خود تفاسیر سے لی گئی ہے، ہماری طرف سے نہیں۔",
    },
    {
      step: "۳",
      label: "بازیافت",
      detail:
        "آپ کا سوال ایک آیت تک پہنچایا جاتا ہے، پھر اقتباسات تین طریقوں سے بیک وقت ڈھونڈے جاتے ہیں: آیت کے دائرے سے، الفاظ سے، اور معنی سے۔ نتائج درجے کی بنیاد پر ملائے جاتے ہیں، اور ہر کتاب کا حصہ محدود رکھا جاتا ہے تاکہ کوئی طویل تفسیر کسی مختصر کو دبا نہ دے۔",
    },
    {
      step: "۴",
      label: "تصدیق",
      detail:
        "تفہُّم جو کچھ لکھتا ہے، اسے جملہ بہ جملہ اُس اقتباس سے ملایا جاتا ہے جس کا وہ دعویٰ کرتا ہے۔ جو جملہ ماخذ تک نہ پہنچے وہ آپ کے دیکھنے سے پہلے حذف کر دیا جاتا ہے، اور حذف شدہ کی تعداد آپ کو دکھائی جاتی ہے۔",
    },
    {
      step: "۵",
      label: "تالیف",
      detail:
        "خلاصے میں صرف وہی شامل ہوتا ہے جو تصدیق سے گزرا، اور اس پر نشان لگا ہوتا ہے کہ یہ تفہُّم کا لکھا ہوا ہے، تاکہ کسی مفسر کا کلام نہ سمجھا جائے۔",
    },
    {
      step: "۶",
      label: "حوالہ",
      detail:
        "ہر اقتباس کے ساتھ کتاب اور مصنف ہوتا ہے، اُس اصل ماخذ فائل کا لنک جس سے وہ داخل ہوا، اور ایک سیڑھی جو بتاتی ہے کہ وہ حوالہ حقیقتاً کہاں تک پہنچتا ہے۔ مجموعے کی کسی کتاب کے لیے جلد اور صفحہ درج نہیں، اور سیڑھی یہ چھپاتی نہیں بلکہ دکھاتی ہے۔",
    },
  ],

  sections: [
    {
      id: "reading",
      title: "تلاش کا خانہ اور مطالعے کا صفحہ",
      body: [
        "عام زبان میں سوال لکھیے۔ آیت کا نمبر جاننا ضروری نہیں: آیت الکرسی اور نیند کے بارے میں سوال ۲:۲۵۵ تک پہنچتا ہے، اور جانچ کی سطح آپ کو دکھاتی ہے کہ کیسے۔",
        "اگر سوال ایک آیت تک پہنچے تو مطالعے کا صفحہ آتا ہے، جو آیت کو جزو بہ جزو کھولتا ہے اور ہر جزو پر ہر مفسر کا کلام دکھاتا ہے۔ اگر کئی آیات تک پہنچے تو شواہد کا صفحہ آتا ہے، جو موازنے کے لیے زیادہ مناسب ہے۔",
      ],
      controls: [
        {
          name: "تلاش",
          where: "صفحے کے اوپر",
          detail:
            "اردو، عربی اور انگریزی قبول کرتا ہے۔ آپ جو بھی لکھیں، تلاش عربی میں چلتی ہے، کیونکہ تفاسیر عربی میں ہیں، اور انہیں آپ کے سوال سے ملانے کے لیے ترجمہ کرنا ماخذ کے بجائے ترجمے میں تلاش ہوتا۔",
        },
        {
          name: "آیت کا خانہ",
          where: "مطالعے کے صفحے کے کنارے",
          detail:
            "آیت اور ایک شائع شدہ ترجمہ، جو اپنی جگہ ٹھہرے رہتے ہیں جبکہ ساتھ تفسیر چلتی رہتی ہے۔ یہ سائٹ کا واحد حصہ ہے جسے سنہری رنگ کی اجازت ہے، تاکہ منزل متن اور تفسیر میں فرق پڑھے بغیر نظر آ جائے۔",
        },
        {
          name: "اس آیت کے اجزا",
          where: "کنارے کے خانے میں آیت کے نیچے",
          detail:
            "ہر وہ جزو جس پر مفسرین نے الگ بات کی، اور ساتھ ان کی تعداد۔ کلک کر کے وہاں پہنچیے۔ جس جزو کو کسی نے الگ نہیں لیا، اسے خالی عنوان دکھانے کے بجائے ساتھ والے میں شامل کر دیا جاتا ہے، کیونکہ خالی عنوان یہ تاثر دیتا ہے کہ روایت خاموش رہی۔",
        },
      ],
    },
    {
      id: "depth",
      title: "سطح کا بٹن",
      body: [
        "ایک بٹن یہ بدلتا ہے کہ شواہد کے گرد کتنا سامان کھینچا جائے۔ یہ نہیں بدلتا کہ کن مآخذ میں تلاش ہو، اور کسی مفسر کو بتائے بغیر ہٹاتا نہیں۔ آپ کا انتخاب آپ ہی کے آلے پر محفوظ رہتا ہے۔",
      ],
      controls: [
        {
          name: "سیکھنا",
          where: "سرنامہ",
          detail:
            "ترجمہ سب سے آگے رہتا ہے اور خود کھل جاتا ہے، کیونکہ اس سطح پر ترجمہ ہی مقصود ہے۔ عربی ایک بٹن کے پیچھے چلی جاتی ہے اور ہمیشہ ایک کلک کے فاصلے پر رہتی ہے۔ ہر جزو پر دو مفسر آگے ہوتے ہیں اور باقی ایک بٹن کے پیچھے، جس پر ان کی تعداد لکھی ہوتی ہے۔",
        },
        {
          name: "مطالعہ",
          where: "سرنامہ",
          detail:
            "طے شدہ سطح۔ ہر جزو پر تمام مفسرین، پہلے عربی اور طلب پر ترجمہ۔ یہی دیانت دار انتخاب ہے، کیونکہ سیکھنا مفسرین چھپاتا ہے اور جانچ وہ سامان دکھاتی ہے جو اکثر قارئین نے مانگا ہی نہیں۔",
        },
        {
          name: "جانچ",
          where: "سرنامہ",
          detail:
            "ہر اقتباس کے نیچے ایک ریکارڈ: اس کا حوالہ کہاں تک پہنچتا ہے، وہ جزو سے کس بنیاد پر اور کتنے اعتماد سے جوڑا گیا، اور اسی جزو پر اس کتاب کے کتنے اور اقتباس موجود ہیں۔ صفحے کے اوپر مجموعے کی کمیاں بھی بتاتی ہے۔",
        },
      ],
    },
    {
      id: "sources",
      title: "مآخذ کا انتخاب",
      body: [
        "آپ طے کرتے ہیں کہ کن کتابوں میں تلاش ہو۔ فہرست میں ہر کتاب کا مسلک اور منہج درج ہے جہاں کوئی مرجع انہیں بیان کرتا ہے، باقی کو اندازے کے بجائے غیر مصنف رکھا گیا ہے۔",
      ],
      controls: [
        {
          name: "مآخذ",
          where: "تلاش کے خانے کے نیچے",
          detail:
            "تیار مجموعے اور انفرادی کتابیں۔ عدد بتاتا ہے کہ آپ کا موجودہ انتخاب حقیقتاً کتنے اقتباسات میں تلاش کرتا ہے، تاکہ تنگ انتخاب مکمل نہ لگے۔",
        },
        {
          name: "مسلک اور منہج کے نشانات",
          where: "مآخذ کی فہرست میں",
          detail:
            "ایک ثانوی مرجع سے لیے گئے ہیں اور آزادانہ تصدیق شدہ نہیں، اسی لیے ان پر یہ درج ہے۔ جس کتاب کو وہ مرجع درج نہیں کرتا، اسے قیاس سے مسلک دینے کے بجائے غیر مصنف دکھایا جاتا ہے۔",
        },
      ],
    },
    {
      id: "passages",
      title: "اقتباس پڑھنا",
      body: [
        "ہر تفسیری کارڈ منقول متن ہے۔ اس میں کچھ بھی تفہُّم کا لکھا ہوا نہیں، اور عربی ہمیشہ موجود رہتی ہے خواہ اوپر ترجمہ دکھایا جا رہا ہو۔",
      ],
      controls: [
        {
          name: "پورا اقتباس دکھائیں",
          where: "ہر کارڈ پر",
          detail: "کارڈ پہلے ابتدائی حصہ دکھاتے ہیں۔ یہ پورا اقتباس جوں کا توں کھول دیتا ہے۔",
        },
        {
          name: "اپنی زبان میں ترجمہ",
          where: "ہر کارڈ پر",
          detail:
            "مشینی ترجمہ پیدا کرتا ہے، اور ہمیشہ اس پر یہی نشان ہوتا ہے۔ یہ عربی کی جگہ کبھی نہیں لیتا، اور اگر کسی حصے کا ترجمہ نہ ہو سکے تو کارڈ بتاتا ہے کہ کتنے جملے کم ہیں، ادھورا ترجمہ مکمل بنا کر پیش نہیں کرتا۔",
        },
        {
          name: "صرف لفظی مشابہت، اقتباس نہیں",
          where: "بعض کارڈوں پر، مطالعہ اور جانچ کی سطح پر",
          detail:
            "ایک تنبیہ۔ یہ اقتباس جزو سے اس لیے جوڑا گیا کہ الفاظ ملتے ہیں، اس لیے نہیں کہ مفسر نے جزو کو قوسین میں لکھا۔ یہ کمزور دعویٰ ہے اور اسی لیے نشان زد ہے تاکہ آپ اسے الگ تولیں۔",
        },
      ],
    },
    {
      id: "conclusion",
      title: "خلاصہ، اور آپ اسے کیوں جانچ سکتے ہیں",
      body: [
        "خلاصہ سائٹ کا واحد متن ہے جو تفہُّم کا لکھا ہوا ہے، منقول نہیں۔ یہ الگ رنگ میں اور نشان کے ساتھ آتا ہے، تاکہ کبھی کسی مفسر کا کلام نہ سمجھا جائے۔",
        "یہ صرف نیچے دکھائے گئے اقتباسات سے لکھا جاتا ہے۔ ماڈل کو اقتباسات بغیر مصنف کے نام، کتاب کے عنوان اور تاریخ کے دیے جاتے ہیں، تاکہ وہ طبری کے بارے میں اپنی پہلے سے معلوم باتیں لکھنے کے بجائے سامنے کے متن کی بات لکھے۔",
        "پھر ہر جملہ اس اقتباس سے ماپا جاتا ہے جس کا حوالہ وہ دیتا ہے۔ جس جملے کی تائید وہ اقتباس نہ کرے وہ حذف ہو جاتا ہے، اسی طرح وہ جو صرف آیت دہرائے، اور وہ جو خلاصے کے بجائے لفظ بہ لفظ نقل کرے۔",
      ],
      controls: [
        {
          name: "لکھے گئے، رکھے گئے، حذف شدہ جملے",
          where: "خلاصے کے نیچے",
          detail:
            "چھلنی کا اپنا ریکارڈ۔ جس خلاصے نے تین جملے پھینکے وہ اُس سے زیادہ قابل اعتماد ہے جو دعویٰ کرے کہ اس نے کچھ نہیں پھینکا، اسی لیے اعداد چھپائے نہیں جاتے۔",
        },
        {
          name: "اوسط تائید",
          where: "خلاصے کے نیچے",
          detail:
            "بچے ہوئے جملے اوسطاً اپنے اقتباسات پر کتنے مضبوط کھڑے ہیں۔ یہ ایک پیمائش ہے جسے آپ خود دوبارہ نکال سکتے ہیں، ماڈل کا اپنے بارے میں دیا ہوا اعتماد نہیں۔",
        },
        {
          name: "حذف شدہ جملے دکھائیں",
          where: "خلاصے کے نیچے",
          detail: "کیا کاٹا گیا اور کیوں۔ مسترد شدہ دکھانا ہی اصل بات ہے: یہی ثبوت ہے کہ چھلنی کام کرتی ہے۔",
        },
      ],
    },
    {
      id: "citations",
      title: "حوالے اور سند کی سیڑھی",
      body: [
        "ہر اقتباس پر نمبر ہے، اور نمبر صفحے کے نیچے مراجع کی فہرست سے ملتے ہیں۔",
        "سیڑھی یوں چلتی ہے: کتاب، طبع، جلد، صفحہ، عکس۔ بھرا ہوا نقطہ یعنی یہ درجہ پہنچ گیا، خالی نقطہ یعنی وہ مجموعے میں موجود نہیں، اور اسے حذف کرنے کے بجائے کھینچا جاتا ہے تاکہ سرسری پڑھنے والے سے کمی نہ چھوٹے۔ فی الحال ہر اقتباس میں صرف پہلا درجہ بھرا ہوتا ہے، کیونکہ برقی متن کے پیچھے کی مطبوعہ طبع متعین نہیں۔",
      ],
      controls: [
        {
          name: "مراجع کی فہرست",
          where: "مطالعے کے صفحے کے آخر میں",
          detail: "ہر شریک ماخذ کا مصنف، کتاب، طبع اور صفحہ، ان کے پہلے ظہور کی ترتیب سے۔",
        },
        {
          name: "یہ جواب کیسے بنا",
          where: "جانچ کی سطح",
          detail:
            "بازیافت کا نشان: آپ کا سوال کیا سمجھا گیا، حقیقتاً کن عربی الفاظ سے تلاش ہوئی، کس طریقے نے کیا پایا، اور کون سے اصول لاگو ہوئے۔",
        },
      ],
    },
  ],

  neverTitle: "تفہُّم کیا نہیں کرے گا",
  neverNote:
    "یہ نظام کے ذریعے نافذ ہیں، محض نیک نیتی پر نہیں چھوڑے گئے۔ ان میں سے کئی ڈیٹابیس کی پابندیاں ہیں، یعنی ڈیٹا ایسی صورت میں محفوظ ہو ہی نہیں سکتا جو انہیں توڑے۔",
  never: [
    "کوئی حوالہ، صفحہ نمبر، نقل یا مفسر گھڑنا۔",
    "ترجمے کو اصل متن بنا کر پیش کرنا۔",
    "ایسے اجماع کا دعویٰ جو اس کے مآخذ بیان نہ کرتے ہوں۔",
    "ایسا اصول محفوظ کرنا جو شرعی حجیت کا دعویٰ کرے مگر اس حجیت کا ماخذ درج نہ ہو۔",
    "داخل ہونے کے بعد کسی اقتباس میں ترمیم۔ اصل متن ناقابل تبدیل ہے اور ڈیٹابیس یہ پابندی لگاتا ہے۔",
    "ایسا لکھا ہوا جملہ دکھانا جو کسی اقتباس تک نہ پہنچایا جا سکے۔",
    "کوئی شرعی فتویٰ دینا، یا یہ بتانا کہ آپ کو کیا ماننا چاہیے۔",
  ],

  gapsTitle: "جو ابھی مکمل نہیں",
  gapsNote: "یہ صفحہ آپ سے اعتماد کا تقاضا کرتے ہوئے ان کمیوں کو چھپائے تو بددیانتی ہوگی۔",
  gaps: [
    {
      name: "حوالہ کتاب کا نام دیتا ہے، اس میں کوئی مقام نہیں",
      detail:
        "یہ اس صفحے کی سب سے اہم حد ہے۔ متن ایک برقی مجموعے سے آیا ہے جو اصل مطبوعہ طبع کی نشاندہی نہیں کرتا، اس لیے مجموعے کے کسی اقتباس پر جلد یا صفحہ درج نہیں، اور نہ کوئی عکس ہے۔ یہاں حوالہ آپ کو بتاتا ہے کہ کس مفسر نے کہا، اور وہی ماخذ فائل نکال کر دیتا ہے جو ہم نے داخل کی، مگر یہ آپ کو کسی مطبوعہ مقام تک نہیں لے جائے گا۔ کسی متعین تحقیق سے ملانا آپ کا کام رہے گا، ہمارا نہیں۔",
    },
    {
      name: "طبعات کے حقوق نامعلوم",
      detail:
        "متن ایک کھلے مجموعے سے آیا ہے جو اصل مطبوعہ طبع کی نشاندہی نہیں کرتا، اس لیے ہر طبع کی حقوقی حیثیت نامعلوم درج ہے، اسے صاف فرض نہیں کیا گیا۔",
    },
    {
      name: "معنوی تلاش فعال نہیں",
      detail:
        "ترتیب فی الحال آیت کی ساخت اور الفاظ پر ہے۔ تیسرا طریقہ موجود ہے مگر ابھی اس کے پیچھے ڈیٹا نہیں، اس لیے ممکن ہے وہ اقتباس سامنے نہ آئے جو آپ کے سوال پر مختلف الفاظ میں بات کرتا ہو۔",
    },
    {
      name: "ترجمے مشینی ہیں",
      detail:
        "اس سائٹ کا کوئی ترجمہ کسی انسانی مترجم نے نہیں دیکھا۔ جہاں بھی آئیں ان پر مشینی ترجمے کا نشان ہوتا ہے، اور عربی ہمیشہ ساتھ دکھائی جاتی ہے۔",
    },
    {
      name: "احاطہ جزوی ہے",
      detail:
        "مجموعہ کتاب بہ کتاب بڑھتا ہے۔ اگر کوئی مفسر کسی آیت پر نظر نہ آئے تو ممکن ہے اس کی کتاب پوری داخل نہ ہوئی ہو، نہ کہ وہ خاموش رہا ہو۔ یہاں غیر حاضری خاموشی کا ثبوت نہیں۔",
    },
  ],

  checkTitle: "ہمیں کیسے جانچیں",
  check: [
    "جانچ کی سطح پر جائیں اور نشان پڑھیں: یہ بتاتا ہے کہ کچھ بھی نکالنے سے پہلے آپ کا سوال کیا سمجھا گیا۔",
    "کسی بھی خلاصے کے حذف شدہ جملے کھولیں۔ اگر کبھی کچھ حذف نہ ہو تو چھلنی کام نہیں کر رہی۔",
    "کوئی حوالہ لے کر مطبوعہ طبع تک جائیں۔ جلد اور صفحہ اسی کے لیے درج ہیں۔",
    "ترجمے کو ساتھ رکھی عربی سے ملائیں۔ دونوں اسی لیے ساتھ دکھائے جاتے ہیں۔",
    "اپنے مآخذ ایک کتاب تک محدود کریں اور دیکھیں کہ خلاصہ بدلتا ہے یا نہیں۔ بدلنا چاہیے۔",
  ],
  contactTitle: "رابطہ، تصحیح اور اشتراک",
  contactBody:
    "تفہُّم سدیس خالد کا بنایا اور سنبھالا ہوا ہے۔ اگر آپ کو کوئی غلطی، غلط نسبت، ناقص ترجمہ، یا کسی اور مفسر کے نام لگا ہوا اقتباس ملے تو براہ کرم مطلع کیجیے۔ اس مواد کو جاننے والوں کی تصحیحات ہی وہ تیز ترین راستہ ہیں جس سے یہ کام قابل اعتماد بنے گا، اور وہ بلا تامل خوش آئند ہیں۔",
  contactCorrections:
    "تجاویز اور اشتراک بھی اتنے ہی خوش آئند ہیں، خاص طور پر ان علما کی طرف سے جو ان متون کے پیچھے کی مطبوعہ طبعات کی نشاندہی کر سکیں، جو اوپر درج سب سے بڑی کمی ہے۔",
  contactEmail: "ای میل",
  contactWhatsapp: "واٹس ایپ",
  contactSite: "ویب سائٹ",
  ownership: "تفہُّم سدیس خالد کا کام ہے۔",
};

export const GUIDE: Record<UiLanguage, Guide> = { en, ar, ur };
