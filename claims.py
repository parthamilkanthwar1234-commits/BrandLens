"""Claim verification: supported / contradicted / expired / unverifiable against approved facts."""
import re
from datetime import date
from .models import BrandPack, Finding
from .checks import SUPERLATIVES, find_claims
from .clauses import tokens

_NUM = re.compile(r"\d[\d,\.]*")

def _raw(s): return [n.rstrip(".,") for n in _NUM.findall(s)]
def _nums(s): return {n.replace(",", "") for n in _raw(s)}

def verify_claims(text: str, pack: BrandPack) -> list[Finding]:
    out, today = [], date.today().isoformat()
    for claim in find_claims(text):
        start = text.find(claim)
        base = dict(quote=claim, start=start if start >= 0 else None, end=start + len(claim) if start >= 0 else None, category="claim")
        best, overlap = None, 0.0
        ct = set(tokens(claim))
        for f in pack.facts:
            ft = set(tokens(f.statement))
            if not ft: continue
            o = len(ct & ft) / len(ft)
            if o > overlap: best, overlap = f, o
        if best and overlap >= 0.5:
            if best.expires and best.expires < today:
                out.append(Finding(**base, severity="medium", source_id=best.id, needs_human=True,
                    reason=f"This matches approved fact {best.id}, but that fact expired on {best.expires}.",
                    suggestion="Confirm the offer or figure is still valid, or remove the claim."))
            elif _nums(claim) and _nums(best.statement) and not (_nums(claim) & _nums(best.statement)):
                rep = None
                cn, fn = _raw(claim), _raw(best.statement)
                if len(cn) == 1 and len(fn) == 1: rep = claim.replace(cn[0], fn[0])
                out.append(Finding(**base, severity="high", source_id=best.id, needs_human=True, replacement=rep,
                    reason=f"Contradicts approved fact {best.id}: \"{best.statement}\".",
                    suggestion="Use the approved figure." if rep else f"Rewrite using the approved fact: \"{best.statement}\"."))
        else:
            sev = "high" if SUPERLATIVES.search(claim) else "medium"
            out.append(Finding(**base, severity=sev, source_id=pack.claim_clause or "NO-APPROVED-FACT", confidence=0.6, needs_human=True,
                reason="No approved fact supports this claim, so it cannot be published as written.",
                suggestion="Remove the claim, or ask a reviewer to add an approved fact that supports it."))
    return out
