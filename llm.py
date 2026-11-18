"""AI judgement checks (tone/messaging) using Google Gemini; optional without an API key."""
import json, os, re
from dotenv import load_dotenv
load_dotenv()
import httpx
from .models import Clause, Finding
from .clauses import retrieve

PROMPT = """You review marketing content against numbered brand guideline clauses.
Return ONLY JSON: {\"findings\":[{\"category\":\"tone|messaging\",\"severity\":\"low|medium|high\",\"quote\":\"exact substring of CONTENT\",\"reason\":\"...\",\"source_id\":\"clause id from CLAUSES\",\"suggestion\":\"rewrite preserving intent\",\"confidence\":0.0}]}
Only report an issue if a clause below directly supports it. If none, return {\"findings\":[]}.

CLAUSES:\n{clauses}\nCONTENT:\n{content}
"""

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def ai_checks(text: str, clauses: list[Clause], client=None, model: str = DEFAULT_MODEL) -> list[Finding]:
    if not text.strip() or not clauses:
        return []
    ctx = retrieve(clauses, text, k=6) or clauses[:6]
    api_key = os.getenv("GEMINI_API_KEY")
    if client is None and not api_key:
        return []
    prompt = PROMPT.format(clauses="\n".join(f"[{c.id}] {c.text}" for c in ctx), content=text)
    try:
        if client is not None:
            # Test/injected clients may provide a Gemini-like generate_content method.
            response = client.generate_content(prompt)
            raw = response.text
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            response = httpx.post(url, params={"key": api_key}, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1500,
                                   "responseMimeType": "application/json"}
            }, timeout=30)
            response.raise_for_status()
            raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return []
    try:
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception:
        return []
    out = []
    for d in data.get("findings", []):
        try:
            out.append(Finding(origin="ai", **d))
        except Exception:
            continue
    return out
