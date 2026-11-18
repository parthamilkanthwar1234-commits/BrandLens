# CodeZen India 2026 — BrandLens Round 2 Submission Notes

## Project
**BrandLens** — AI-assisted brand governance and content review.

## Core workflow
1. A creator enters copy or uploads a supported content file.
2. BrandLens evaluates the content against approved guidelines, facts, terminology and visual checks.
3. Findings show severity, exact quote, rule/fact reference, rationale and suggested correction.
4. Creator accepts/dismisses findings with a reason when required, then submits for review.
5. Reviewer verifies claims; brand manager makes the final approve/request-changes decision.

## Completed features
- Content review for text and supported uploads (DOCX, PDF, TXT, PNG, JPG)
- Deterministic checks for terminology, facts/claims and visual identity/contrast
- AI tone and messaging review through Google Gemini API
- Rule-grounded finding validation (AI findings must match guideline IDs and content excerpts)
- Severity labels and correction suggestions
- Creator/reviewer/manager role workflow
- Versioning, history, audit events and insights/dashboard
- Sample content/demo brand pack

## Technology and implementation
- Python, FastAPI, Pydantic
- SQLite persistence
- HTML/CSS/JavaScript frontend
- Google Gemini REST API `generateContent` (default model: `gemini-2.5-flash`)
- Document extraction: python-docx, pdfplumber; image analysis via Pillow
- Deployment container: Docker


## Changes from the original plan
- Replaced Anthropic Claude integration with Google Gemini so the team can run AI review using its available Gemini API key.
- AI provider is optional: without `GEMINI_API_KEY`, deterministic checks still run and the app remains usable.
- Uses Gemini JSON output mode, low temperature, and the existing grounding/validation pipeline to reduce unsupported findings.


## Round 3 — Three major product improvements
1. **Custom brand workspace and guideline ingestion:** allow each organization to upload its brand book, extract clauses, approved claims, terms and colors, and manage versions instead of using the current demo brand pack.
2. **Multimodal creative review:** review uploaded social/ad images and layouts for logo placement, typography, brand colors, accessibility, and copy/image consistency, with annotated evidence.
3. **Team collaboration and approval integrations:** secure multi-tenant accounts, reviewer assignment, approval notifications, and integrations/export to common publishing workflows.

## Validation
Automated tests: **6 passed** locally with `PYTHONPATH=.`. Tests cover clause numbering, contrast math, grounding validation, role permissions, approval workflow, and claim verification.


## Submission links (fill before submitting)
- Live project: [ADD PUBLIC DEPLOYMENT URL]
- Source repository: [ADD PUBLIC GITHUB/GIT URL]
- Project PDF: Updated Project Report (included in this package)


## Deployment checklist
- Configure `GEMINI_API_KEY` in the host's environment/secrets settings (never commit it).
- Open the live app in an incognito/private browser and test the main review workflow.
- Test the project without signing in (if applicable) and ensure the link is public.
- Confirm sample content produces findings and a clean sample can be approved.
