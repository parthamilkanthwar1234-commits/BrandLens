"""Citation validator: the 'no evidence, no flag' rule."""
from .models import Finding, BrandPack, Clause

STATIC_SOURCES = {"WCAG-1.4.3", "WCAG-1.1.1", "PALETTE", "NO-APPROVED-FACT"}

def valid_source_ids(pack: BrandPack, clauses: list[Clause]) -> set[str]:
    ids = set(STATIC_SOURCES) | {c.id for c in clauses} | {f.id for f in pack.facts}
    ids |= {"TERMS:" + k.lower() for k in pack.preferred_terms}
    return ids

def validate(findings: list[Finding], content: str, pack: BrandPack, clauses: list[Clause]):
    """Return (kept, downgraded, dropped). A finding must cite a real source and quote real content;
    ungrounded AI findings are downgraded to 'needs human check' or dropped."""
    ok_ids = valid_source_ids(pack, clauses)
    kept, down, dropped = [], [], []
    for f in findings:
        quote_ok = f.category in {"accessibility", "visual"} or f.quote.lower() in content.lower()
        src_ok = f.source_id in ok_ids
        if quote_ok and src_ok:
            kept.append(f)
        elif quote_ok and f.origin == "ai":
            f.needs_human, f.confidence, f.source_id = True, min(f.confidence, 0.4), "UNGROUNDED"
            down.append(f)
        else:
            dropped.append(f)
    return kept, down, dropped
