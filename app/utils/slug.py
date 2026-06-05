import re
from typing import Optional


def make_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text


def slug_tokens(slug: str) -> list[str]:
    return [t for t in re.split(r"[-_]", slug.lower()) if t]


def token_matches_slug(slug: str, query: str) -> bool:
    tokens = slug_tokens(slug)
    q_tokens = [t for t in re.split(r"[\s-]+", query.lower().strip()) if t]
    if not q_tokens:
        return False
    for qt in q_tokens:
        if not any(qt == t or t.startswith(qt) or qt.startswith(t) for t in tokens):
            return False
    return True


DEVICE_PREFIXES = {
    "iphone": "iphone",
    "samsung": "samsung",
    "xiaomi": "xiaomi",
    "redmi": "xiaomi",
    "poco": "xiaomi",
    "huawei": "huawei",
    "honor": "honor",
    "pixel": "pixel",
    "oppo": "oppo",
    "vivo": "vivo",
    "oneplus": "oneplus",
    "nokia": "nokia",
    "lg": "lg",
    "zte": "zte",
    "motorola": "motorola",
    "moto": "motorola",
    "realme": "realme",
    "nothing": "nothing",
    "infinix": "infinix",
    "tecno": "tecno",
    "itel": "itel",
    "hmd": "nokia",
    "sony": "sony",
    "xperia": "sony",
    "ipad": "apple",
    "apple": "apple",
    "macbook": "apple",
}


def brand_from_slug(slug: str) -> Optional[str]:
    tokens = slug_tokens(slug)
    if not tokens:
        return None
    first = tokens[0]
    normalized = DEVICE_PREFIXES.get(first, first)
    return normalized


def slug_search_score(slug: str, query: str) -> int:
    q_lower = query.lower().strip()
    q_tokens = [t for t in re.split(r"[\s-]+", q_lower) if t]
    if not q_tokens:
        return 0

    tokens = slug_tokens(slug)
    normalized = [DEVICE_PREFIXES.get(t, t) for t in tokens]
    score = 0

    exact = q_lower in slug.lower()
    if exact:
        score += 10

    all_tokens_matched = True
    token_matches = 0
    for qt in q_tokens:
        nqt = DEVICE_PREFIXES.get(qt, qt)
        matched = False
        for t in normalized:
            if nqt == t or t.startswith(nqt) or nqt.startswith(t):
                matched = True
                token_matches += 1
                break
        if not matched:
            all_tokens_matched = False

    if all_tokens_matched and q_tokens:
        score += 5
    score += token_matches

    return score


def matches_slug_query(slug: str, query: str) -> bool:
    tokens = slug_tokens(slug)
    q_raw = query.lower().strip()
    q_tokens = [t for t in re.split(r"[\s-]+", q_raw) if t]
    if not q_tokens:
        return False

    if q_raw in slug.lower():
        return True

    normalized = [DEVICE_PREFIXES.get(t, t) for t in tokens]
    for qt in q_tokens:
        nqt = DEVICE_PREFIXES.get(qt, qt)
        if not any(nqt == t or t.startswith(nqt) or nqt.startswith(t) for t in normalized):
            return False
    return True
