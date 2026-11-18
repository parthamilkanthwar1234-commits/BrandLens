# BrandLens — Round 2

BrandLens is a brand-governance review tool for marketing copy and assets. Submit text or upload a supported file, run a review against approved brand rules/facts/terminology, inspect findings with their source rules and suggested corrections, and keep human approval as the final decision.


## Run locally

Requirements: Python 3.10+.

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; on macOS/Linux use cp .env.example .env
# Add your Google Gemini key to .env (GEMINI_API_KEY=...)
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The app works without a Gemini key using deterministic rule/fact/visual checks; AI tone and messaging review is enabled when `GEMINI_API_KEY` is configured.


## Gemini configuration
- Provider: Google Gemini API (REST, `generateContent`)
- Default model: `gemini-2.5-flash` (override with `GEMINI_MODEL`)
- Key: `GEMINI_API_KEY`
- AI output is constrained to JSON and validated against guideline IDs and exact content quotes by the existing validation pipeline.


## Features
- Text review and file extraction (.docx, .pdf, .txt, .png, .jpg)
- Brand guideline clause retrieval and rule-grounded findings
- Terminology, approved-fact/claim, and visual color/contrast checks
- AI-assisted tone and messaging review via Gemini (optional key)
- Findings include severity, quoted text, source rule, rationale, suggested fix and confidence
- Creator/reviewer/brand-manager workflow with review submission, claim verification, approvals and change requests
- Version history and audit activity
- Dashboard and insights
- Human decision remains final


## Environment variables
See `.env.example`.


## Tests
```bash
cd backend
pytest -q
```

## Notes
The app's demo brand pack and demo activity are seeded locally. For a production deployment, configure a persistent database, secure authentication/authorization, rate limits, secrets management and tenant isolation.
