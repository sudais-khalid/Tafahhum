"""The Tafsir catalogue.

Maps the works available from the ingestion source to the metadata a reader
needs in order to choose between them: who wrote it, when, which school a named
reference assigns it to, and what kind of commentary it is.

Every `tradition` and `method` value here is attributed to
`CLASSIFICATION_SOURCE`. None of it is asserted on Tafahhum's own authority, and
`UNCLASSIFIED` is used wherever the source does not say — an honest gap rather
than an inference from the author's reputation.

Death years likewise: they are recorded only where the source states them, and
the bibliographical layer (Phase 3) is what will establish the rest with
page-level attestations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CLASSIFICATION_SOURCE = "List of tafsir works (Wikipedia)"
CLASSIFICATION_SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_tafsir_works"
CLASSIFICATION_SLUG = "wikipedia-list-of-tafsir-works"


@dataclass(frozen=True)
class CatalogueEntry:
    """One work offered for selection."""

    slug: str                 # Tafahhum slug
    source_slug: str          # slug in the ingestion source
    title_ar: str
    title_en: str
    author_ar: str
    author_en: str
    death_hijri: int | None   # only where the reference states it
    tradition: str
    method: str
    rank: int                 # catalogue ordering; roughly chronological
    default: bool = False     # in the default selection
    note: str | None = None
    covers_all_ayahs: bool = True
    aliases: tuple[str, ...] = field(default_factory=tuple)


#: Works the reference classifies under a Sunni heading (Sunni, Sunni Sufi,
#: Sunni Salafi), plus the non-Sunni and unclassified works the source offers.
#: Non-Sunni works are catalogued rather than hidden: a researcher may want them,
#: and silently dropping a work would misrepresent the corpus.
CATALOGUE: tuple[CatalogueEntry, ...] = (
    # ---- transmitted-report commentaries (bi-al-ma'thur) ------------------
    CatalogueEntry(
        "tabari-jami-al-bayan", "ar-tafsir-al-tabari",
        "جامع البيان عن تأويل آي القرآن", "Jami al-Bayan an Tawil Ay al-Quran",
        "محمد بن جرير الطبري", "Muhammad ibn Jarir al-Tabari",
        None, "SUNNI", "BI_AL_MATHUR", rank=10, default=True,
        aliases=("tabari", "طبري"),
    ),
    CatalogueEntry(
        "ibn-abi-hatim-tafsir", "tafsir-ibn-abi-hatim",
        "تفسير القرآن العظيم", "Tafsir al-Quran al-Azim (Ibn Abi Hatim)",
        "عبد الرحمن بن أبي حاتم الرازي", "Abd al-Rahman Ibn Abi Hatim al-Razi",
        None, "SUNNI", "BI_AL_MATHUR", rank=12,
    ),
    CatalogueEntry(
        "samarqandi-bahr-al-ulum", "tafsir-al-samarqandi",
        "بحر العلوم", "Bahr al-Ulum",
        "أبو الليث السمرقندي", "Abu al-Layth al-Samarqandi",
        None, "UNCLASSIFIED", "BI_AL_MATHUR", rank=14,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "ibn-abi-zamanin-tafsir", "tafsir-ibn-abi-zamanin",
        "تفسير ابن أبي زمنين", "Tafsir Ibn Abi Zamanin",
        "ابن أبي زمنين", "Ibn Abi Zamanin",
        None, "UNCLASSIFIED", "BI_AL_MATHUR", rank=15,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "samani-tafsir", "tafsir-al-sam-ani",
        "تفسير السمعاني", "Tafsir al-Sam'ani",
        "أبو المظفر السمعاني", "Abu al-Muzaffar al-Sam'ani",
        None, "UNCLASSIFIED", "BI_AL_MATHUR", rank=16,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "baghawi-maalim-al-tanzil", "ar-tafsir-al-baghawi",
        "معالم التنزيل", "Maalim al-Tanzil",
        "الحسين بن مسعود البغوي", "al-Husayn ibn Masud al-Baghawi",
        None, "UNCLASSIFIED", "BI_AL_MATHUR", rank=18, default=True,
        note="Not listed in the classification reference; school not asserted.",
        aliases=("baghawi", "بغوي"),
    ),
    CatalogueEntry(
        "ibn-kathir-tafsir-al-quran-al-azim", "ar-tafsir-ibn-kathir",
        "تفسير القرآن العظيم", "Tafsir al-Quran al-Azim",
        "إسماعيل بن عمر ابن كثير", "Ismail ibn Umar Ibn Kathir",
        774, "SUNNI", "BI_AL_MATHUR", rank=40, default=True,
        aliases=("kathir", "كثير"),
    ),
    CatalogueEntry(
        "suyuti-al-durr-al-manthur", "al-durr-al-manthur",
        "الدر المنثور في التفسير بالمأثور", "Al-Durr al-Manthur",
        "جلال الدين السيوطي", "Jalal al-Din al-Suyuti",
        911, "SUNNI", "BI_AL_MATHUR", rank=55,
        aliases=("suyuti", "سيوطي"),
    ),
    CatalogueEntry(
        "mawsuat-al-tafsir-al-mathur", "mawsoo-at-al-tafsir-al-ma-thoor",
        "موسوعة التفسير المأثور", "Mawsuat al-Tafsir al-Ma'thur",
        "مجموعة من الباحثين", "Compiled by a research team",
        None, "UNCLASSIFIED", "BI_AL_MATHUR", rank=95,
        note="Modern compilation; not listed in the classification reference.",
    ),

    # ---- considered-opinion commentaries (bi-al-ra'y) ---------------------
    CatalogueEntry(
        "mawardi-al-nukat-wa-al-uyun", "tafsir-al-mawardi",
        "النكت والعيون", "An-Nukat wa al-Uyun",
        "أبو الحسن الماوردي", "Abu al-Hasan al-Mawardi",
        450, "SUNNI", "BI_AL_RAY", rank=20,
    ),
    CatalogueEntry(
        "wahidi-al-wajiz", "al-wajiz-wahidi",
        "الوجيز في تفسير الكتاب العزيز", "Al-Wajiz",
        "أبو الحسن الواحدي", "Abu al-Hasan al-Wahidi",
        None, "SUNNI", "BI_AL_RAY", rank=21,
    ),
    CatalogueEntry(
        "wahidi-al-basit", "al-basit",
        "البسيط", "Al-Basit",
        "أبو الحسن الواحدي", "Abu al-Hasan al-Wahidi",
        None, "SUNNI", "BI_AL_RAY", rank=22,
    ),
    CatalogueEntry(
        "ibn-atiyyah-al-muharrar-al-wajiz", "al-muharrar-al-wajiz-ibn-atiyyah",
        "المحرر الوجيز", "Al-Muharrar al-Wajiz",
        "عبد الحق بن غالب ابن عطية", "Abd al-Haqq ibn Ghalib Ibn Atiyyah",
        541, "SUNNI", "BI_AL_RAY", rank=24, default=True,
        aliases=("atiyyah", "عطية"),
    ),
    CatalogueEntry(
        "ibn-al-jawzi-zad-al-masir", "tafsir-ibn-al-jawzi",
        "زاد المسير في علم التفسير", "Zad al-Masir fi Ilm al-Tafsir",
        "أبو الفرج ابن الجوزي", "Abu al-Faraj Ibn al-Jawzi",
        597, "SUNNI", "BI_AL_RAY", rank=26,
    ),
    CatalogueEntry(
        "razi-mafatih-al-ghayb", "tafsir-al-razi",
        "مفاتيح الغيب", "Mafatih al-Ghayb",
        "فخر الدين الرازي", "Fakhr al-Din al-Razi",
        606, "SUNNI", "KALAMI", rank=28, default=True,
        aliases=("razi", "رازي"),
    ),
    CatalogueEntry(
        "baydawi-anwar-al-tanzil", "tafsir-al-baydawi",
        "أنوار التنزيل وأسرار التأويل", "Anwar al-Tanzil wa Asrar al-Tawil",
        "عبد الله بن عمر البيضاوي", "Abdullah ibn Umar al-Baydawi",
        685, "SUNNI", "MIXED", rank=32, default=True,
        aliases=("baydawi", "بيضاوي"),
    ),
    CatalogueEntry(
        "nasafi-madarik-al-tanzil", "tafsir-al-nasafi",
        "مدارك التنزيل وحقائق التأويل", "Madarik al-Tanzil wa Haqaiq al-Tawil",
        "أبو البركات النسفي", "Abu al-Barakat al-Nasafi",
        710, "SUNNI", "MIXED", rank=34,
    ),
    CatalogueEntry(
        "abu-hayyan-al-bahr-al-muhit", "al-bahr-al-muhit",
        "البحر المحيط", "Al-Bahr al-Muhit",
        "أبو حيان الأندلسي", "Abu Hayyan al-Gharnati",
        745, "SUNNI", "LUGHAWI", rank=36,
    ),
    CatalogueEntry(
        "ibn-qayyim-tafsir", "tafsir-ibn-al-qayyim",
        "بدائع التفسير", "Badai al-Tafsir",
        "ابن قيم الجوزية", "Ibn Qayyim al-Jawziyya",
        751, "SUNNI", "MIXED", rank=38,
    ),
    CatalogueEntry(
        "ibn-juzay-al-tashil", "tafsir-ibn-juzay",
        "التسهيل لعلوم التنزيل", "Al-Tashil li-Ulum al-Tanzil",
        "ابن جزي الكلبي", "Ibn Juzayy al-Kalbi",
        758, "SUNNI", "MIXED", rank=39,
    ),
    CatalogueEntry(
        "ibn-adil-al-lubab", "al-lubab-fi-ulum-al-kitab",
        "اللباب في علوم الكتاب", "Al-Lubab fi Ulum al-Kitab",
        "ابن عادل الدمشقي", "Ibn Adil al-Dimashqi",
        None, "UNCLASSIFIED", "MIXED", rank=42,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "thaalibi-al-jawahir-al-hisan", "ar-tafsir-al-tha-alibi",
        "الجواهر الحسان في تفسير القرآن", "Al-Jawahir al-Hisan",
        "عبد الرحمن الثعالبي", "Abd al-Rahman al-Thaalibi",
        None, "SUNNI", "BI_AL_MATHUR", rank=44,
    ),
    CatalogueEntry(
        "biqai-nazm-al-durar", "nazam-al-durar-al-biqa-i",
        "نظم الدرر في تناسب الآيات والسور", "Nazm al-Durar",
        "برهان الدين البقاعي", "Burhan al-Din al-Biqai",
        None, "SUNNI", "BALAGHI", rank=46,
    ),
    CatalogueEntry(
        "jalalayn", "ar-tafsir-al-jalalayn",
        "تفسير الجلالين", "Tafsir al-Jalalayn",
        "جلال الدين المحلي وجلال الدين السيوطي",
        "Jalal al-Din al-Mahalli and Jalal al-Din al-Suyuti",
        None, "SUNNI", "MIXED", rank=50, default=True,
        aliases=("jalalayn", "جلالين"),
    ),
    CatalogueEntry(
        "abu-suud-irshad-al-aql", "tafsir-abi-al-su-ood",
        "إرشاد العقل السليم إلى مزايا الكتاب الكريم", "Irshad al-Aql al-Salim",
        "أبو السعود العمادي", "Abu al-Suud al-Imadi",
        951, "SUNNI", "BALAGHI", rank=58,
    ),
    CatalogueEntry(
        "qurtubi-al-jami-li-ahkam", "ar-tafseer-al-qurtubi",
        "الجامع لأحكام القرآن", "Al-Jami li-Ahkam al-Quran",
        "محمد بن أحمد القرطبي", "Muhammad ibn Ahmad al-Qurtubi",
        671, "SUNNI", "FIQHI", rank=30, default=True,
        aliases=("qurtubi", "قرطبي"),
    ),

    # ---- Sufi / allusive ---------------------------------------------------
    CatalogueEntry(
        "iji-jami-al-bayan", "jamia-al-bayan-aliji",
        "جامع البيان في تفسير القرآن", "Jami al-Bayan (al-Iji)",
        "الإيجي", "al-Iji",
        None, "UNCLASSIFIED", "MIXED", rank=48,
        note="Not listed in the classification reference; school not asserted.",
    ),

    # ---- later and modern Sunni -------------------------------------------
    CatalogueEntry(
        "shawkani-fath-al-qadir", "fath-al-qadir-al-shawkani",
        "فتح القدير", "Fath al-Qadir",
        "محمد بن علي الشوكاني", "Muhammad ibn Ali al-Shawkani",
        None, "SUNNI_SALAFI", "MIXED", rank=60, default=True,
        aliases=("shawkani", "شوكاني"),
    ),
    CatalogueEntry(
        "alusi-ruh-al-maani", "tafsir-al-alusi",
        "روح المعاني", "Ruh al-Maani",
        "محمود الألوسي", "Mahmud al-Alusi",
        1270, "SUNNI", "MIXED", rank=62, default=True,
        aliases=("alusi", "آلوسي"),
    ),
    CatalogueEntry(
        "qanuji-fath-al-bayan", "fath-al-bayan-li-al-qanuji",
        "فتح البيان في مقاصد القرآن", "Fath al-Bayan",
        "صديق حسن خان القنوجي", "Siddiq Hasan Khan al-Qanuji",
        None, "UNCLASSIFIED", "MIXED", rank=64,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "qasimi-mahasin-al-tawil", "mahasin-al-ta-wil-al-qasimi",
        "محاسن التأويل", "Mahasin al-Tawil",
        "جمال الدين القاسمي", "Jamal al-Din al-Qasimi",
        None, "UNCLASSIFIED", "MIXED", rank=66,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "saadi-taysir-al-karim", "ar-tafsir-as-saadi",
        "تيسير الكريم الرحمن", "Taysir al-Karim al-Rahman",
        "عبد الرحمن بن ناصر السعدي", "Abd al-Rahman ibn Nasir al-Sadi",
        None, "SUNNI_SALAFI", "MIXED", rank=68, default=True,
        aliases=("saadi", "sadi", "سعدي"),
    ),
    CatalogueEntry(
        "shanqiti-adwa-al-bayan", "adwa-al-bayan",
        "أضواء البيان", "Adwa al-Bayan",
        "محمد الأمين الشنقيطي", "Muhammad al-Amin al-Shanqiti",
        None, "UNCLASSIFIED", "MIXED", rank=70,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "ibn-ashur-al-tahrir-wa-al-tanwir", "ar-tafseer-tahrir-al-tanwir",
        "التحرير والتنوير", "Al-Tahrir wa al-Tanwir",
        "محمد الطاهر ابن عاشور", "Muhammad al-Tahir Ibn Ashur",
        None, "MODERNIST", "BALAGHI", rank=72, default=True,
        aliases=("ashur", "عاشور"),
    ),
    CatalogueEntry(
        "ibn-uthaymeen-tafsir", "tafsir-ibn-uthaymeen",
        "تفسير ابن عثيمين", "Tafsir Ibn Uthaymin",
        "محمد بن صالح العثيمين", "Muhammad ibn Salih al-Uthaymin",
        None, "UNCLASSIFIED", "MIXED", rank=74,
        note="Not listed in the classification reference; school not asserted.",
    ),
    CatalogueEntry(
        "jazairi-aysar-al-tafasir", "abu-bakr-jabir-al-jazairi",
        "أيسر التفاسير", "Aysar al-Tafasir",
        "أبو بكر جابر الجزائري", "Abu Bakr Jabir al-Jazairi",
        None, "SUNNI", "MIXED", rank=76,
    ),
    CatalogueEntry(
        "tantawi-al-tafsir-al-wasit", "ar-tafsir-al-wasit",
        "التفسير الوسيط", "Al-Tafsir al-Wasit",
        "محمد سيد طنطاوي", "Muhammad Sayyid Tantawi",
        None, "SUNNI", "MIXED", rank=78,
    ),
    CatalogueEntry(
        "al-tafsir-al-muyassar", "ar-tafsir-muyassar",
        "التفسير الميسر", "Al-Tafsir al-Muyassar",
        "نخبة من العلماء", "A committee of scholars",
        None, "UNCLASSIFIED", "MIXED", rank=80,
        note="Modern committee work; not listed in the classification reference.",
    ),
    CatalogueEntry(
        "al-mukhtasar-fi-al-tafsir", "ar-tafsir-al-mukhtasar",
        "المختصر في التفسير", "Al-Mukhtasar fi al-Tafsir",
        "مركز تفسير للدراسات القرآنية", "Tafsir Center for Quranic Studies",
        None, "UNCLASSIFIED", "MIXED", rank=82,
        note="Modern institutional work; not listed in the classification reference.",
    ),
    CatalogueEntry(
        "tadabbur-wa-amal", "tadabbur-wa-amal",
        "تدبر وعمل", "Tadabbur wa Amal",
        "مشروع تدبر", "Tadabbur project",
        None, "UNCLASSIFIED", "MIXED", rank=84,
        note="Modern devotional work; not listed in the classification reference.",
    ),

    # ---- non-Sunni, catalogued and clearly labelled ------------------------
    CatalogueEntry(
        "zamakhshari-al-kashshaf", "al-kashshaf-al-zamakhshari",
        "الكشاف عن حقائق التنزيل", "Al-Kashshaf an Haqaiq al-Tanzil",
        "محمود بن عمر الزمخشري", "Mahmud ibn Umar al-Zamakhshari",
        539, "MUTAZILA", "BALAGHI", rank=90,
        note=(
            "The classification reference places this work under Mu'tazila. It is "
            "excluded from the Sunni selection and remains available on request."
        ),
        aliases=("zamakhshari", "زمخشري", "kashshaf"),
    ),
    # Tanwir al-Miqbas is deliberately absent.
    #
    # The upstream endpoint ar-tafseer-tanwir-al-miqbas does not serve Tanwir
    # al-Miqbas. It serves Ibn Ashur's al-Tahrir wa al-Tanwir, the same text
    # already catalogued under ibn-ashur-al-tahrir-wa-al-tanwir: across surahs
    # 2, 18, 36, 55 and 112, 70% of ayahs are over 90% word-identical, and the
    # remainder differ only in vocalisation. The two slugs share the word
    # "tanwir", which is the likely origin of the mix-up upstream.
    #
    # Ingesting it would attribute Ibn Ashur (d. 1393 AH) to Ibn Abbas
    # (d. 68 AH), a gap of thirteen centuries, and would do so with a citation
    # that looks entirely well-formed. Nothing downstream could catch that,
    # because every other check this system runs would pass. It stays out until
    # a source is found that serves the actual work.

    # ---- linguistic and qira'at apparatus ---------------------------------
    # Catalogued separately: these are tools for reading the Quran rather than
    # commentaries on its meaning, and mixing them into a Tafsir result set
    # would answer a different question than the one asked.
    CatalogueEntry(
        "samin-al-halabi-al-durr-al-masun", "al-dur-al-masun-lil-samin-al-halabi",
        "الدر المصون", "Al-Durr al-Masun",
        "السمين الحلبي", "al-Samin al-Halabi",
        None, "UNCLASSIFIED", "LUGHAWI", rank=200,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "irab-al-quran-al-darwish", "i-rab-al-quran-li-al-darwish",
        "إعراب القرآن وبيانه", "Irab al-Quran wa Bayanuh",
        "محيي الدين الدرويش", "Muhyi al-Din al-Darwish",
        None, "UNCLASSIFIED", "LUGHAWI", rank=202,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-jadwal-fi-irab-al-quran", "al-jadwal-fi-i-rab-al-quran",
        "الجدول في إعراب القرآن", "Al-Jadwal fi Irab al-Quran",
        "محمود صافي", "Mahmud Safi",
        None, "UNCLASSIFIED", "LUGHAWI", rank=204,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-irab-al-muyassar", "al-i-rab-al-muyassar",
        "الإعراب الميسر", "Al-Irab al-Muyassar",
        "نخبة من العلماء", "A committee of scholars",
        None, "UNCLASSIFIED", "LUGHAWI", rank=206,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-muyassar-fi-gharib-al-quran", "al-muyassar-fi-al-gharib",
        "الميسر في غريب القرآن", "Al-Muyassar fi Gharib al-Quran",
        "نخبة من العلماء", "A committee of scholars",
        None, "UNCLASSIFIED", "GHARIB", rank=210,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-siraj-fi-gharib-al-quran", "asseraj-fi-bayan-gharib-alquran",
        "السراج في بيان غريب القرآن", "Al-Siraj fi Bayan Gharib al-Quran",
        "محمد الخضيري", "Muhammad al-Khudayri",
        None, "UNCLASSIFIED", "GHARIB", rank=212,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-nashr-ibn-al-jazari", "al-nashr-li-ibn-al-jazari",
        "النشر في القراءات العشر", "Al-Nashr fi al-Qiraat al-Ashr",
        "ابن الجزري", "Ibn al-Jazari",
        None, "UNCLASSIFIED", "QIRAAT", rank=220,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
    CatalogueEntry(
        "al-mawsuah-al-quraniyyah-lil-qiraat", "al-qira-at-al-mawsoo-ah-al-qur-aniyyah",
        "الموسوعة القرآنية في القراءات", "Al-Mawsuah al-Quraniyyah fi al-Qiraat",
        "مجموعة من الباحثين", "Compiled by a research team",
        None, "UNCLASSIFIED", "QIRAAT", rank=222,
        note=(
            "Linguistic and recitation apparatus; the classification "
            "reference lists works of tafsir, not works of this kind."
        ),
    ),
)

BY_SLUG = {e.slug: e for e in CATALOGUE}
BY_SOURCE_SLUG = {e.source_slug: e for e in CATALOGUE}

#: Headings the classification reference groups under Sunni.
SUNNI_TRADITIONS = ("SUNNI", "SUNNI_SUFI", "SUNNI_SALAFI")

#: Methods that comment on meaning, as opposed to grammar or recitation.
COMMENTARY_METHODS = (
    "BI_AL_MATHUR", "BI_AL_RAY", "FIQHI", "BALAGHI", "SUFI_ISHARI", "KALAMI", "MIXED"
)


def sunni_works() -> list[CatalogueEntry]:
    """Works a named reference classifies under a Sunni heading."""
    return [e for e in CATALOGUE if e.tradition in SUNNI_TRADITIONS]


def unclassified_works() -> list[CatalogueEntry]:
    """Works no consulted reference classifies. Shown, never silently dropped."""
    return [e for e in CATALOGUE if e.tradition == "UNCLASSIFIED"]


def commentaries() -> list[CatalogueEntry]:
    """Works that comment on meaning, excluding grammar and qira'at apparatus."""
    return [e for e in CATALOGUE if e.method in COMMENTARY_METHODS]


def default_selection() -> list[CatalogueEntry]:
    """The starting selection: broad coverage across method and era."""
    return sorted((e for e in CATALOGUE if e.default), key=lambda e: e.rank)


def work_terms() -> dict[str, str]:
    """Searchable name fragments for query classification."""
    out: dict[str, str] = {}
    for entry in CATALOGUE:
        for alias in entry.aliases:
            out.setdefault(alias.lower(), entry.slug)
    return out
