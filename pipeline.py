from .models import BrandPack, ReviewRequest
from .clauses import split_clauses
from .checks import run_deterministic
from .claims import verify_claims
from .llm import ai_checks
from .validate import validate

def review(req: ReviewRequest, pack: BrandPack, client=None) -> dict:
    clauses = split_clauses(pack.guidelines_text)
    raw = run_deterministic(req, pack) + verify_claims(req.text, pack) + ai_checks(req.text, clauses, client)
    seen, uniq = set(), []
    for f in raw:
        k = (f.category, f.quote, f.source_id)
        if k not in seen: seen.add(k); uniq.append(f)
    kept, down, dropped = validate(uniq, req.text, pack, clauses)
    order = {"high": 0, "medium": 1, "low": 2}
    findings = sorted(kept + down, key=lambda f: order[f.severity])
    return {"findings": [f.model_dump() for f in findings], "dropped_ungrounded": len(dropped),
            "clauses_indexed": len(clauses)}
