import os, tempfile
os.environ["BRANDLENS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from fastapi.testclient import TestClient
from app.main import app
from app.models import Finding
from app.clauses import split_clauses
from app.validate import validate
from app.checks import contrast_ratio
from app.seed import demo_pack, GUIDELINES, SAMPLES

H = lambda r: {"X-Role": r}

def test_clauses_numbered():
    ids = [c.id for c in split_clauses(GUIDELINES)]
    assert ids[0] == "G1.1" and "G3.2" in ids and "G5.1" in ids

def test_contrast_math():
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0

def test_ungrounded_ai_finding_is_downgraded_or_dropped():
    pack, cl = demo_pack(), split_clauses(GUIDELINES)
    fake_cite = Finding(category="tone", severity="high", quote="hello", reason="x", source_id="G99.9", origin="ai")
    fake_quote = Finding(category="tone", severity="high", quote="not in text", reason="x", source_id="G1.1", origin="ai")
    good = Finding(category="tone", severity="low", quote="hello", reason="x", source_id="G1.1", origin="ai")
    kept, down, dropped = validate([fake_cite, fake_quote, good], "hello world", pack, cl)
    assert kept == [good] and len(down) == 1 and down[0].needs_human and len(dropped) == 1

def test_full_workflow_and_roles():
    with TestClient(app) as c:
        s = SAMPLES[0]
        d = c.post("/api/submissions", json=s, headers=H("creator")).json()
        assert all(f["source_id"] for f in d["findings"])                       # every finding cites a rule
        cats = {(f["category"], f["source_id"]) for f in d["findings"]}
        assert ("terminology", "G2.1") in cats and ("claim", "F2") in cats and ("claim", "G3.2") in cats
        assert c.post("/api/submissions", json=s, headers=H("manager")).status_code == 403   # role enforced
        assert c.post(f"/api/submissions/{d['id']}/submit", headers=H("creator")).status_code == 409  # open high findings
        # dismiss needs a reason
        assert c.post(f"/api/submissions/{d['id']}/actions", json={"index": 0, "action": "dismissed", "reason": ""}, headers=H("creator")).status_code == 400
        # clean draft goes through the whole approval chain
        clean = c.post("/api/submissions", json=SAMPLES[2], headers=H("creator")).json()
        assert clean["findings"] == []
        assert c.post(f"/api/submissions/{clean['id']}/submit", headers=H("creator")).json()["status"] == "in_review"
        assert c.post(f"/api/submissions/{clean['id']}/decision", json={"decision": "approve"}, headers=H("creator")).status_code == 403
        ok = c.post(f"/api/submissions/{clean['id']}/decision", json={"decision": "approve"}, headers=H("manager")).json()
        assert ok["status"] == "approved"

def test_manager_cannot_approve_unverified_claims():
    with TestClient(app) as c:
        d = c.post("/api/submissions", json={"title": "t", "text": "Orbit was founded in 2018."}, headers=H("creator")).json()
        assert d["findings"][0]["needs_human"]
        # high finding must be dismissed with reason before submit
        assert c.post(f"/api/submissions/{d['id']}/actions", json={"index": 0, "action": "dismissed", "reason": "checking"}, headers=H("creator")).status_code == 200
        assert c.post(f"/api/submissions/{d['id']}/submit", headers=H("creator")).status_code == 200
        r = c.post(f"/api/submissions/{d['id']}/decision", json={"decision": "approve"}, headers=H("manager"))
        assert r.status_code == 409 and "reviewer" in r.json()["detail"]
        c.post(f"/api/submissions/{d['id']}/signoff", json={"index": 0, "verdict": "verified"}, headers=H("reviewer"))
        assert c.post(f"/api/submissions/{d['id']}/decision", json={"decision": "approve"}, headers=H("manager")).json()["status"] == "approved"

def test_insights_flags_unclear_rule():
    with TestClient(app) as c:
        rules = {r["source_id"]: r for r in c.get("/api/insights").json()["rules"]}
        assert rules["G1.1"]["unclear"] is True
