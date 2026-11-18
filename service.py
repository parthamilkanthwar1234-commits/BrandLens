import json, time
from . import db
from .models import BrandPack, ReviewRequest
from .pipeline import review
from .seed import demo_pack, HISTORY

ROLES = {"creator": "Riya Sharma (Creator)", "reviewer": "Karan Mehta (Legal reviewer)", "manager": "Anita Desai (Brand manager)"}
_PACK = None

def pack() -> BrandPack:
    global _PACK
    if _PACK is None: _PACK = demo_pack()
    return _PACK

def create_version(title, channel, author, req: ReviewRequest, doc_id=None, role="creator", at=None):
    res = review(req, pack())
    with db.conn() as c:
        if doc_id is None:
            version = 1
            cur = c.execute("SELECT COALESCE(MAX(doc_id),0)+1 FROM submissions"); doc_id = cur.fetchone()[0]
        else:
            version = c.execute("SELECT COALESCE(MAX(version),0)+1 FROM submissions WHERE doc_id=?", (doc_id,)).fetchone()[0]
        cur = c.execute("INSERT INTO submissions(doc_id,version,title,channel,author,text,req_json,findings_json,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (doc_id, version, title, channel, author, req.text, req.model_dump_json(), json.dumps(res["findings"]), "draft", at or time.time()))
        sid = cur.lastrowid
        db.add_event(c, doc_id, sid, author, role, "checked",
                     f"Version {version} checked: {len(res['findings'])} finding(s).", at)
    return sid

def get(sid):
    with db.conn() as c:
        r = db.row(c.execute("SELECT * FROM submissions WHERE id=?", (sid,)).fetchone())
        if not r: return None
        r["versions"] = [dict(x) for x in c.execute("SELECT id,version,status,created_at FROM submissions WHERE doc_id=? ORDER BY version", (r["doc_id"],))]
        r["events"] = [dict(x) for x in c.execute("SELECT * FROM events WHERE doc_id=? ORDER BY id", (r["doc_id"],))]
        r["is_latest"] = r["versions"][-1]["id"] == sid
        return r

def seed_history():
    """Populate past activity once so the dashboard has data."""
    with db.conn() as c:
        if c.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]: return
    base = time.time() - 86400 * 6
    for i, h in enumerate(HISTORY):
        t = base + i * 3600 * 9
        s1 = create_version(h["title"], h["channel"], h["author"], ReviewRequest(text=h["v1"]), at=t)
        d1 = get(s1)
        acts = {}
        for idx, f in enumerate(d1["findings"]):
            if f["source_id"] in h["dismiss"]:
                acts[str(idx)] = {"action": "dismissed", "reason": h["dismiss"][f["source_id"]], "by": h["author"]}
            elif f.get("replacement") is not None or f["category"] in ("claim", "tone", "terminology"):
                acts[str(idx)] = {"action": "accepted", "reason": "", "by": h["author"]}
        with db.conn() as c:
            c.execute("UPDATE submissions SET actions_json=? WHERE id=?", (json.dumps(acts), s1))
        if h["v2"]:
            s2 = create_version(h["title"], h["channel"], h["author"], ReviewRequest(text=h["v2"]), doc_id=d1["doc_id"], at=t + 1800)
            d2 = get(s2)
            sign = {str(i): {"verdict": "verified", "note": "Checked against fact sheet.", "by": ROLES["reviewer"]}
                    for i, f in enumerate(d2["findings"]) if f["needs_human"]}
            with db.conn() as c:
                c.execute("UPDATE submissions SET status='approved', signoffs_json=? WHERE id=?", (json.dumps(sign), s2))
                db.add_event(c, d1["doc_id"], s2, ROLES["creator"], "creator", "submitted", "Submitted for approval.", t + 2400)
                db.add_event(c, d1["doc_id"], s2, ROLES["manager"], "manager", "approved", "Approved.", t + 3600)
        else:
            with db.conn() as c:
                c.execute("UPDATE submissions SET status='in_review' WHERE id=?", (s1,))
                db.add_event(c, d1["doc_id"], s1, ROLES["creator"], "creator", "submitted", "Submitted for approval.", t + 2400)
