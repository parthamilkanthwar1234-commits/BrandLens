"""Deterministic checks: reproducible, no AI involved."""
import re
from .models import BrandPack, Finding, ReviewRequest

def _rgb(h: str):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def valid_hex(h: str) -> bool:
    return bool(re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", h.strip()))

def _lin(c: int) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

def luminance(h: str) -> float:
    r, g, b = (_lin(x) for x in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)

def colour_distance(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b))) ** 0.5

SUPERLATIVES = re.compile(r"(?<!\w)(#1|number one|the best|best[- ]in[- ]class|world[- ]class|guaranteed?|100% [a-z]+|"
                          r"risk[- ]free|unmatched|unbeatable|India'?s (?:first|best|largest|#1))(?!\w)", re.I)

def _case(src: str, good: str) -> str:
    if src.isupper() and len(src) > 1: return good.upper()
    if src[:1].isupper(): return good[:1].upper() + good[1:]
    return good

def check_terminology(text: str, pack: BrandPack) -> list[Finding]:
    out = []
    for bad, good in pack.preferred_terms.items():
        for m in re.finditer(rf"(?<!\w){re.escape(bad)}(?!\w)", text, re.I):
            src = pack.term_clauses.get(bad, "TERMS:" + bad.lower())
            out.append(Finding(category="terminology", severity="medium", quote=m.group(0), start=m.start(), end=m.end(),
                reason=f"\"{m.group(0)}\" is an avoided term. The approved term is \"{good}\".",
                source_id=src, replacement=_case(m.group(0), good), suggestion=f"Replace with \"{good}\"."))
    return out

def check_tone_rules(text: str, pack: BrandPack) -> list[Finding]:
    out = []
    for r in pack.tone_rules:
        for m in re.finditer(r.pattern, text):
            rep = m.group(0).lower() if r.fix == "lower" else r.fix
            out.append(Finding(category=r.category, severity=r.severity, quote=m.group(0), start=m.start(), end=m.end(),
                reason=r.reason, source_id=r.clause, replacement=rep,
                suggestion=r.advice or (f"Replace with \"{rep}\"." if rep is not None else None)))
    return out

def check_contrast(req: ReviewRequest, pack: BrandPack) -> list[Finding]:
    out = []
    for fg, bg in req.colours:
        if not (valid_hex(fg) and valid_hex(bg)): continue
        r = contrast_ratio(fg, bg)
        if r < pack.min_contrast:
            out.append(Finding(category="accessibility", severity="high", quote=f"{fg} on {bg}",
                reason=f"Text contrast is {r:.2f}:1, below the required {pack.min_contrast}:1 (WCAG 2.1 AA).",
                source_id="WCAG-1.4.3", suggestion="Darken the text colour or lighten the background until the ratio reaches 4.5:1."))
    return out

def check_palette(req: ReviewRequest, pack: BrandPack, tol: float = 60.0) -> list[Finding]:
    if not pack.palette: return []
    used = [c for pair in req.colours for c in pair] + list(req.image_colours)
    out, seen = [], set()
    for c in used:
        if not valid_hex(c) or c.upper() in seen: continue
        seen.add(c.upper())
        near = min(pack.palette, key=lambda p: colour_distance(c, p))
        d = colour_distance(c, near)
        if d > tol:
            out.append(Finding(category="visual", severity="medium", quote=c.upper(), source_id="PALETTE",
                reason=f"{c.upper()} is not in the approved palette (nearest approved colour {near.upper()}, distance {d:.0f}).",
                replacement=None, suggestion=f"Use an approved colour such as {near.upper()}."))
    return out

def check_alt(req: ReviewRequest) -> list[Finding]:
    if req.images_missing_alt:
        return [Finding(category="accessibility", severity="high", quote=f"{req.images_missing_alt} image(s)", source_id="WCAG-1.1.1",
            reason="Images without alternative text cannot be understood by screen-reader users.",
            suggestion="Add a short description of each image as alternative text.")]
    return []

def find_claims(text: str) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sents if re.search(r"\d|%", s) or SUPERLATIVES.search(s)]

def run_deterministic(req: ReviewRequest, pack: BrandPack) -> list[Finding]:
    return (check_terminology(req.text, pack) + check_tone_rules(req.text, pack)
            + check_contrast(req, pack) + check_palette(req, pack) + check_alt(req))
