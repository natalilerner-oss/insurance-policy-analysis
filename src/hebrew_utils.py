import re

HEBREW_RANGE = re.compile(r"[\u0590-\u05FF]")


def contains_hebrew(text: str) -> bool:
    if not text:
        return False
    return bool(HEBREW_RANGE.search(text))


def normalize_hebrew(text: str) -> str:
    if not text:
        return text
    return text.replace("\u200f", "").replace("\u200e", "").strip()


def rtl_wrap(text: str) -> str:
    if not text:
        return text
    return f"\u202B{text}\u202C"
