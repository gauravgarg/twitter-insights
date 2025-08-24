import re

def normalize_keyword(s: str) -> str:
    # Trim, collapse spaces, unify case, remove weird unicode dashes
    s = (s or "").strip().replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.upper()

def build_match_patterns(keywords):
    """
    Create robust regex patterns to detect tickers/company names in tweets:
    - Match bare words: TCS
    - With $ or #: $TCS, #TCS
    - Handle hyphens: BAJAJ-AUTO
    """
    patterns = []
    for kw in keywords:
        kw_norm = normalize_keyword(kw)
        # Escape regex special chars except hyphen (keep it literal)
        kw_esc = re.sub(r"([.^$*+?{}\\[\]|()])", r"\\\1", kw_norm)
        # Word-ish boundaries: start or non-word, allow $/# before, end or non-word
        pat = rf"(?<![A-Z0-9])(?:\$|#)?{kw_esc}(?![A-Z0-9])"
        patterns.append(re.compile(pat, re.IGNORECASE))
    return patterns

def find_first_match(text: str, patterns):
    for p in patterns:
        m = p.search(text or "")
        if m:
            return m.group(0)  # matched token
    return None
