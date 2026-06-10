# canonical key -> aliases / substrings that mean that stack
STACK_ALIASES: dict[str, tuple[str, ...]] = {
    "frontend": (
        "frontend",
        "front-end",
        "front end",
        "frontend developer",
        "frontend development",
        "frontend-development",
        "frontedn",  # typo
        "fe dev",
    ),
    "backend": (
        "backend",
        "back-end",
        "back end",
        "backend developer",
        "server-side",
    ),
    "fullstack": (
        "fullstack",
        "full stack",
        "full-stack",
        "mern",
        "mean",
    ),
    "mobile": ("mobile", "ios", "android", "react native", "flutter"),
    "devops": ("devops", "sre", "platform engineer"),
}

def _normalize(raw: str) -> str:
    """lowercase, strip, collapse separators"""
    s = (raw or "").strip().lower()
    for ch in "-_/.":
        s = s.replace(ch, " ")
    return " ".join(s.split())  # collapse whitespace


# precompute: normalized alias -> canonical
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in STACK_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[_normalize(alias)] = canonical


def normalize_stack(raw: str | None) -> str:
    norm = _normalize(raw)
    if not norm:
        return "unknown"

    # 1) exact alias hit
    if norm in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[norm]

    # 2) substring / keyword hit (handles "senior frontend developer react")
    for canonical, aliases in STACK_ALIASES.items():
        for alias in aliases:
            if _normalize(alias) in norm:
                return canonical

    # 3) fallback: cleaned raw string (or "other")
    return norm  # or return "other"