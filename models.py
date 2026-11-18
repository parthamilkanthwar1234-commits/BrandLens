from pydantic import BaseModel, Field
from typing import Optional

class Fact(BaseModel):
    id: str
    statement: str
    source: str = ""
    expires: Optional[str] = None  # ISO date

class ToneRule(BaseModel):
    pattern: str
    clause: str
    reason: str
    severity: str = "medium"
    category: str = "tone"
    fix: Optional[str] = None      # literal replacement, or "lower"
    advice: Optional[str] = None

class BrandPack(BaseModel):
    name: str = "Organisation"
    guidelines_text: str
    facts: list[Fact] = []
    preferred_terms: dict[str, str] = {}   # avoided -> preferred
    term_clauses: dict[str, str] = {}      # avoided -> clause id
    tone_rules: list[ToneRule] = []
    palette: list[str] = []
    min_contrast: float = 4.5
    claim_clause: Optional[str] = None     # clause cited for unsupported claims

class Clause(BaseModel):
    id: str
    text: str

class Finding(BaseModel):
    category: str    # tone | terminology | messaging | visual | accessibility | claim
    severity: str    # low | medium | high
    quote: str
    reason: str
    source_id: str
    confidence: float = 1.0
    suggestion: Optional[str] = None
    replacement: Optional[str] = None   # text that can replace `quote` directly
    start: Optional[int] = None
    end: Optional[int] = None
    origin: str = "rule"                # rule | ai
    needs_human: bool = False

class ReviewRequest(BaseModel):
    text: str = ""
    colours: list[tuple[str, str]] = Field(default_factory=list)   # (foreground, background)
    image_colours: list[str] = Field(default_factory=list)
    images_missing_alt: int = 0
