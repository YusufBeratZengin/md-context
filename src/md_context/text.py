"""Unicode normalization shared by indexing and retrieval."""

import re
import unicodedata


def normalize(text: str, strip_diacritics: bool = False) -> str:
    """Fold case, including all Turkish i variants; optionally remove accents."""
    text = unicodedata.normalize("NFC", text).replace("İ", "i").replace("ı", "i")
    text = text.casefold().replace("i\u0307", "i")
    if strip_diacritics:
        text = "".join(
            char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
        )
    return unicodedata.normalize("NFC", text)


def tokenize(text: str, strip_diacritics: bool = False) -> list[str]:
    return re.findall(r"[^\W_]+", normalize(text, strip_diacritics), flags=re.UNICODE)
