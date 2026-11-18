import re
from .models import Clause

_HEAD = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+(.*\S)\s*$")

def split_clauses(text: str) -> list[Clause]:
    """Split guideline text into citable clauses. Numbered lines ('3.2 Use ...') keep their
    number as id; unnumbered paragraphs get sequential ids."""
    out, auto = [], 0
    for block in re.split(r"\n\s*\n|\n(?=\s*\d+(?:\.\d+)*[.)]?\s)", text.strip()):
        block = " ".join(block.split())
        if not block:
            continue
        m = _HEAD.match(block)
        if m:
            out.append(Clause(id="G" + m.group(1), text=m.group(2)))
        else:
            auto += 1
            out.append(Clause(id=f"G-p{auto}", text=block))
    return out

_TOK = re.compile(r"[a-z0-9']+")
_STOP = set("the a an and or of to in is are be for with on at by it this that as from".split())

def tokens(s: str) -> list[str]:
    return [t for t in _TOK.findall(s.lower()) if t not in _STOP]

def retrieve(clauses: list[Clause], query: str, k: int = 5) -> list[Clause]:
    """Lightweight lexical retrieval (swap for pgvector embeddings in Round 2 build)."""
    q = set(tokens(query))
    scored = []
    for c in clauses:
        ct = set(tokens(c.text))
        if not ct:
            continue
        score = len(q & ct) / (len(ct) ** 0.5)
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for s, c in scored[:k] if s > 0]
