"""Demo organisation 'Orbit Learning' (fictional) used so judges can try the product with zero setup."""
from .models import BrandPack, Fact, ToneRule

GUIDELINES = """1.1 Voice: write in a warm, clear and friendly voice. Avoid hype and exaggeration.
1.2 Use at most one exclamation mark per piece. Never stack exclamation marks.
1.3 Do not use ALL CAPS for emphasis.
2.1 Always call our customers "learners". Never call them "users" or "students".
2.2 Refer to the product as "Orbit". Never write "the app" or "Orbit App".
2.3 Say "course", not "class".
3.1 State only facts that appear in the approved fact sheet. Numbers must match the fact sheet exactly.
3.2 Never promise guaranteed outcomes such as a job, placement, salary or results.
3.3 Avoid superlatives such as "best" or "#1" unless an approved fact supports them.
4.1 Primary colours are navy #14213D and white #FFFFFF. The accent colour is amber #FCA311.
4.2 Text must meet WCAG AA contrast of at least 4.5:1.
4.3 Every image must have alternative text.
5.1 Lead with the learner's benefit. Position Orbit as a practical skill-building platform, not a replacement for a degree."""

def demo_pack() -> BrandPack:
    return BrandPack(
        name="Orbit Learning (demo)",
        guidelines_text=GUIDELINES,
        facts=[
            Fact(id="F1", statement="Orbit was founded in 2021", source="Company profile"),
            Fact(id="F2", statement="Over 50000 learners have joined Orbit", source="Dashboard, Oct 2026"),
            Fact(id="F3", statement="Orbit offers 120 courses", source="Course catalogue"),
            Fact(id="F4", statement="All Orbit courses are self-paced", source="Product page"),
            Fact(id="F5", statement="Orbit has partnered with 40 colleges", source="Partnerships sheet"),
            Fact(id="F6", statement="The summer sale gives learners 20% off", source="Campaign brief", expires="2026-08-31"),
        ],
        preferred_terms={"users": "learners", "user": "learner", "students": "learners", "student": "learner",
                         "class": "course", "classes": "courses"},
        term_clauses={k: "G2.1" for k in ("users", "user", "students", "student")} | {"class": "G2.3", "classes": "G2.3"},
        tone_rules=[
            ToneRule(pattern=r"!{2,}", clause="G1.2", severity="medium", fix="!", reason="Stacked exclamation marks break the warm, calm voice."),
            ToneRule(pattern=r"\b[A-Z]{4,}\b", clause="G1.3", severity="low", fix="lower", reason="ALL CAPS reads as shouting. Use normal case for emphasis."),
            ToneRule(pattern=r"(?i)\b(revolutionary|game[- ]changing|mind[- ]blowing|incredible|insane|unbelievable|life[- ]changing)\b", clause="G1.1", severity="medium",
                     reason="Hype wording. The guidelines ask for a clear, factual voice.", advice="Replace with a specific, factual benefit for the learner."),
            ToneRule(pattern=r"(?i)\bguaranteed? (?:job|placement|salary|results?|success)\b|\b100% placement\b", clause="G3.2", severity="high", category="claim",
                     reason="Promises a guaranteed outcome, which Orbit never offers.", advice="Remove the guarantee. Describe what learners practise instead."),
            ToneRule(pattern=r"(?i)\b(the app|Orbit App)\b", clause="G2.2", severity="medium", fix="Orbit", reason="The product name is \"Orbit\"."),
            ToneRule(pattern=r"(?i)\b(replaces?|better than) (?:a |your )?(?:college )?degree\b", clause="G5.1", severity="high", category="messaging",
                     reason="Positions Orbit as a replacement for a degree, which conflicts with the approved messaging.",
                     advice="Say Orbit builds practical skills that complement a degree."),
        ],
        palette=["#14213D", "#FFFFFF", "#FCA311"],
        claim_clause="G3.1",
    )

SAMPLES = [
    {"title": "Instagram launch post", "channel": "Social",
     "text": "Our users LOVE the app!! Join the best platform in India and get a guaranteed job after every class. Over 80,000 learners have joined Orbit.",
     "colours": [["#8A8A8A", "#9A9A9A"]], "images_missing_alt": 1},
    {"title": "Summer sale email", "channel": "Email",
     "text": "Hi there! Our summer sale gives learners 20% off every course. Orbit was founded in 2018 and now offers 120 courses. This revolutionary offer ends soon.",
     "colours": [["#14213D", "#FFFFFF"], ["#FF3B7A", "#FFFFFF"]], "images_missing_alt": 0},
    {"title": "Careers page blurb (already clean)", "channel": "Web",
     "text": "Orbit is a practical skill-building platform. Learners choose from 120 courses and study at their own pace, with every course self-paced. Orbit builds skills that complement a degree.",
     "colours": [["#14213D", "#FFFFFF"]], "images_missing_alt": 0},
]

# Past activity so the insights dashboard is meaningful on first open.
HISTORY = [
    {"title": "Webinar announcement", "channel": "Social", "author": "Riya Sharma",
     "v1": "Join our INCREDIBLE webinar!! Students get a free class.", "v2": "Join our webinar. Learners get a free course.",
     "dismiss": {"G1.1": "Casual social tone, kept intentionally."}},
    {"title": "Campus ambassador ad", "channel": "Social", "author": "Riya Sharma",
     "v1": "This incredible programme is game-changing for users.", "v2": "This programme helps learners build practical skills.",
     "dismiss": {"G1.1": "Hype word was in a quote from a learner."}},
    {"title": "Partner college email", "channel": "Email", "author": "Dev Patel",
     "v1": "Orbit has partnered with 60 colleges. The app is mind-blowing.", "v2": "Orbit has partnered with 40 colleges.",
     "dismiss": {"G1.1": "Unclear whether testimonials count as hype."}},
    {"title": "Product page update", "channel": "Web", "author": "Dev Patel",
     "v1": "Orbit offers 120 courses. All courses are self-paced.", "v2": None, "dismiss": {}},
]
