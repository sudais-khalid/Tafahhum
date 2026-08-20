"""Language detection for the three supported user languages.

Arabic and Urdu share a script, so a generic script check cannot separate them.
The discriminator is that Urdu uses a set of letters that standard Arabic
orthography does not — retroflexes, the noon ghunna, the yeh barree, and the
Persian-derived consonants. Their presence is close to conclusive; their absence
is not, so a short Urdu sentence made only of shared letters falls back to
function-word matching.

Detection is intentionally rule-based rather than model-based. It runs on every
query, must be deterministic so that a query classification is reproducible in the
audit log, and has only three classes to separate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tafahhum.arabic.normalize import arabic_ratio, is_arabic_script
from tafahhum.core.enums import Language

# Letters used in Urdu (and Persian) that standard Arabic orthography does not use.
_URDU_MARKERS = set("ٹڈڑںےہھگچپژۂۓٴ")

# Very common Urdu function words, in normalised form. Used when the text is in
# Arabic script but contains none of the marker letters.
_URDU_FUNCTION_WORDS = {
    "کا", "کی", "کے", "میں", "سے", "پر", "ہے", "ہیں", "نے", "کو",
    "اور", "یہ", "وہ", "کیا", "کیوں", "کہ", "تھا", "تھی", "ہوتا",
    "کرنا", "والے", "والا", "بارے", "مطابق", "تفسیر", "کون", "کہاں",
}

# Common Arabic function words, likewise.
_ARABIC_FUNCTION_WORDS = {
    "في", "من", "على", "عن", "الى", "إلى", "هذا", "هذه", "ذلك", "التي",
    "الذي", "ما", "هل", "كيف", "لماذا", "متى", "اين", "أين", "قال",
    "وقال", "تفسير", "معنى", "الاية", "الآية", "سورة", "بين", "عند",
}

# Urdu- and Arabic-language names for the concept "tafsir", used as a weak signal.
_LATIN_WORD = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class DetectionResult:
    language: Language
    confidence: float
    reason: str

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.language.value} ({self.confidence:.2f}: {self.reason})"


def detect_language(text: str, default: Language = Language.EN) -> DetectionResult:
    """Classify text as Arabic, English, or Urdu.

    `default` is the caller's declared UI language and is used only when the text
    carries no signal at all — an empty string, or bare digits like "2:255".
    """
    stripped = text.strip()
    if not stripped:
        return DetectionResult(default, 0.0, "empty input")

    if not is_arabic_script(stripped):
        if _LATIN_WORD.search(stripped):
            return DetectionResult(Language.EN, 0.95, "latin script")
        # Digits and punctuation only, e.g. "2:255" — carries no language.
        return DetectionResult(default, 0.2, "no linguistic content")

    ratio = arabic_ratio(stripped)

    # Mixed script: Arabic letters plus substantial Latin. Treat the Latin as the
    # carrier language, since a quoted Arabic phrase inside an English question is
    # far more common than the reverse.
    if ratio < 0.5 and _LATIN_WORD.search(stripped):
        return DetectionResult(Language.EN, 0.7, "latin-dominant mixed script")

    marker_hits = sum(1 for c in stripped if c in _URDU_MARKERS)
    if marker_hits:
        confidence = min(0.99, 0.80 + 0.05 * marker_hits)
        return DetectionResult(
            Language.UR, confidence, f"{marker_hits} urdu-specific letter(s)"
        )

    tokens = set(re.findall(r"[؀-ۿ]+", stripped))
    urdu_words = len(tokens & _URDU_FUNCTION_WORDS)
    arabic_words = len(tokens & _ARABIC_FUNCTION_WORDS)

    if urdu_words > arabic_words:
        return DetectionResult(Language.UR, 0.75, "urdu function words")
    if arabic_words > 0:
        return DetectionResult(Language.AR, 0.90, "arabic function words")

    # Arabic script, no distinguishing signal. Arabic is the safer assumption:
    # the corpus is Arabic, so a misrouted Arabic query still retrieves, whereas a
    # misrouted Urdu query would be translated unnecessarily.
    return DetectionResult(Language.AR, 0.60, "arabic script, no marker")
