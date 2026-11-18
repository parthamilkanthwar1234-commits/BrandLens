import io, json, os, re
from collections import Counter, defaultdict
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from . import db, service
from .clauses import split_clauses
from .models import ReviewRequest
from .seed import SAMPLES

app = FastAPI(title="BrandLens API")
STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

@app.on_event("startup")
def _startup():
    db.init(); service.seed_history()

def need(role: Optional[str], *allowed):
    if role not in allowed:
        raise HTTPException(403, f"This action needs the role: {' or '.join(allowed)}. Switch role in the top bar.")
    return service.ROLES[role]

def must_get(sid):
    d = service.get(sid)
    if not d: raise HTTPException(404, "Submission not found")
    return d

@app.get("/api/health")
def health(): return {"ok": True}

@app.get("/api/brand")
def brand():
    p = service.pack()
    return {"name": p.name, "clauses": [c.model_dump() for c in split_clauses(p.guidelines_text)],
            "facts": [f.model_dump() for f in p.facts], "terms": p.preferred_terms, "palette": p.palette,
            "min_contrast": p.min_contrast}

@app.get("/api/samples")
def samples(): return SAMPLES

class NewSub(BaseModel):
    title: str = "Untitled"
    channel: str = "Social"
    text: str = ""
    colours: list[tuple[str, str]] = []
    image_colours: list[str] = []
    images_missing_alt: int = 0
    doc_id: Optional[int] = None

@app.post("/api/submissions")
def create(body: NewSub, x_role: Optional[str] = Header(None)):
    actor = need(x_role, "creator")
    if not body.text.strip() and not body.colours and not body.image_colours:
        raise HTTPException(400, "Add some content to check.")
    if body.doc_id is not None:
        prev = service.get(body.doc_id and _latest_id(body.doc_id))
        if prev is None: raise HTTPException(404, "Document not found")
        if prev["status"] in ("in_review", "approved"):
            raise HTTPException(409, f"This document is {prev['status']} and cannot be edited.")
    req = ReviewRequest(text=body.text, colours=body.colours, image_colours=body.image_colours, images_missing_alt=body.images_missing_alt)
    sid = service.create_version(body.title, body.channel, actor, req, doc_id=body.doc_id)
    return service.get(sid)

def _latest_id(doc_id):
    with db.conn() as c:
        r = c.execute("SELECT id FROM submissions WHERE doc_id=? ORDER BY version DESC LIMIT 1", (doc_id,)).fetchone()
    return r["id"] if r else None

@app.get("/api/submissions")
def listing():
    with db.conn() as c:
        rows = c.execute("""SELECT s.id,s.doc_id,s.version,s.title,s.channel,s.author,s.status,s.created_at,s.findings_json
                            FROM submissions s JOIN (SELECT doc_id, MAX(version) mv FROM submissions GROUP BY doc_id) m
                            ON s.doc_id=m.doc_id AND s.version=m.mv ORDER BY s.created_at DESC""").fetchall()
    out = []
    for r in rows:
        d = dict(r); f = json.loads(d.pop("findings_json"))
        d["findings"] = len(f); d["high"] = sum(1 for x in f if x["severity"] == "high")
        out.append(d)
    return out

@app.get("/api/submissions/{sid}")
def detail(sid: int): return must_get(sid)

class Act(BaseModel):
    index: int
    action: str            # accepted | dismissed
    reason: str = ""

@app.post("/api/submissions/{sid}/actions")
def act(sid: int, body: Act, x_role: Optional[str] = Header(None)):
    actor = need(x_role, "creator"); d = must_get(sid)
    if d["status"] not in ("draft", "changes_requested") or not d["is_latest"]:
        raise HTTPException(409, "Only the latest draft can be edited.")
    if not 0 <= body.index < len(d["findings"]): raise HTTPException(400, "No such finding")
    if body.action not in ("accepted", "dismissed"): raise HTTPException(400, "Unknown action")
    if body.action == "dismissed" and len(body.reason.strip()) < 3:
        raise HTTPException(400, "Please give a reason for dismissing a finding.")
    d["actions"][str(body.index)] = {"action": body.action, "reason": body.reason.strip(), "by": actor}
    with db.conn() as c:
        c.execute("UPDATE submissions SET actions_json=? WHERE id=?", (json.dumps(d["actions"]), sid))
        f = d["findings"][body.index]
        db.add_event(c, d["doc_id"], sid, actor, "creator", body.action,
                     f"{body.action.capitalize()} [{f['source_id']}] \"{f['quote'][:60]}\"" + (f" because: {body.reason.strip()}" if body.reason.strip() else ""))
    return service.get(sid)

@app.post("/api/submissions/{sid}/submit")
def submit(sid: int, x_role: Optional[str] = Header(None)):
    actor = need(x_role, "creator"); d = must_get(sid)
    if d["status"] not in ("draft", "changes_requested") or not d["is_latest"]:
        raise HTTPException(409, "This version cannot be submitted.")
    open_high = [f for i, f in enumerate(d["findings"])
                 if f["severity"] == "high" and d["actions"].get(str(i), {}).get("action") != "dismissed"]
    if open_high:
        raise HTTPException(409, f"{len(open_high)} high-severity finding(s) are still open. Fix them and re-check, or dismiss them with a reason.")
    with db.conn() as c:
        c.execute("UPDATE submissions SET status='in_review' WHERE id=?", (sid,))
        db.add_event(c, d["doc_id"], sid, actor, "creator", "submitted", "Submitted for approval.")
    return service.get(sid)

class Sign(BaseModel):
    index: int
    verdict: str   # verified | rejected
    note: str = ""

@app.post("/api/submissions/{sid}/signoff")
def signoff(sid: int, body: Sign, x_role: Optional[str] = Header(None)):
    actor = need(x_role, "reviewer"); d = must_get(sid)
    if d["status"] != "in_review": raise HTTPException(409, "Only documents in review can be signed off.")
    if not 0 <= body.index < len(d["findings"]) or not d["findings"][body.index]["needs_human"]:
        raise HTTPException(400, "That finding does not need reviewer sign-off.")
    if body.verdict not in ("verified", "rejected"): raise HTTPException(400, "Unknown verdict")
    if body.verdict == "rejected" and not body.note.strip(): raise HTTPException(400, "Add a note when rejecting a claim.")
    d["signoffs"][str(body.index)] = {"verdict": body.verdict, "note": body.note.strip(), "by": actor}
    with db.conn() as c:
        c.execute("UPDATE submissions SET signoffs_json=? WHERE id=?", (json.dumps(d["signoffs"]), sid))
        db.add_event(c, d["doc_id"], sid, actor, "reviewer", "signoff",
                     f"Claim {body.verdict}: \"{d['findings'][body.index]['quote'][:60]}\"" + (f" ({body.note.strip()})" if body.note.strip() else ""))
    return service.get(sid)

class Decision(BaseModel):
    decision: str   # approve | request_changes
    comment: str = ""

@app.post("/api/submissions/{sid}/decision")
def decide(sid: int, body: Decision, x_role: Optional[str] = Header(None)):
    actor = need(x_role, "manager"); d = must_get(sid)
    if d["status"] != "in_review": raise HTTPException(409, "This document is not waiting for approval.")
    if body.decision == "approve":
        pending = [i for i, f in enumerate(d["findings"]) if f["needs_human"] and d["signoffs"].get(str(i), {}).get("verdict") != "verified"]
        if pending:
            raise HTTPException(409, f"{len(pending)} claim(s) still need a reviewer to verify them before approval.")
        status, kind = "approved", "approved"
    elif body.decision == "request_changes":
        if not body.comment.strip(): raise HTTPException(400, "Please explain what needs to change.")
        status, kind = "changes_requested", "changes_requested"
    else:
        raise HTTPException(400, "Unknown decision")
    with db.conn() as c:
        c.execute("UPDATE submissions SET status=? WHERE id=?", (status, sid))
        db.add_event(c, d["doc_id"], sid, actor, "manager", kind, body.comment.strip() or ("Approved." if status == "approved" else ""))
    return service.get(sid)

@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 8_000_000: raise HTTPException(413, "File is too large (limit 8 MB).")
    name = (file.filename or "").lower()
    try:
        if name.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            missing = sum(1 for s in doc.inline_shapes
                          if not (s._inline.docPr.get("descr") or "").strip())
            return {"text": text, "image_colours": [], "images_missing_alt": missing, "filename": file.filename}
        if name.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            return {"text": text, "image_colours": [], "images_missing_alt": 0, "filename": file.filename}
        if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB"); im.thumbnail((200, 200))
            q = im.quantize(colors=6).convert("RGB")
            cols = Counter(q.getdata()).most_common(6)
            return {"text": "", "image_colours": ["#%02X%02X%02X" % c for c, _ in cols], "images_missing_alt": 1, "filename": file.filename,
                    "note": "Colours were read from the image. Alt text is assumed missing until you confirm it."}
        if name.endswith((".txt", ".md")):
            return {"text": data.decode("utf-8", "ignore"), "image_colours": [], "images_missing_alt": 0, "filename": file.filename}
    except Exception:
        raise HTTPException(422, "Could not read that file. Try a different file or paste the text.")
    raise HTTPException(415, "Supported files: .docx, .pdf, .txt, .png, .jpg")

@app.get("/api/insights")
def insights():
    p = service.pack(); clause_text = {c.id: c.text for c in split_clauses(p.guidelines_text)}
    shown, acc, dis, by_cat = Counter(), Counter(), Counter(), Counter()
    reasons = defaultdict(list)
    docs = defaultdict(list)
    with db.conn() as c:
        rows = [db.row(r) for r in c.execute("SELECT * FROM submissions ORDER BY doc_id, version")]
    for r in rows:
        docs[r["doc_id"]].append(r)
        for i, f in enumerate(r["findings"]):
            shown[f["source_id"]] += 1; by_cat[f["category"]] += 1
            a = r["actions"].get(str(i))
            if a:
                (acc if a["action"] == "accepted" else dis)[f["source_id"]] += 1
                if a["action"] == "dismissed" and a["reason"]: reasons[f["source_id"]].append(a["reason"])
    rules = []
    for sid_, n in shown.most_common(10):
        a, d_ = acc[sid_], dis[sid_]
        rate = d_ / (a + d_) if (a + d_) else 0
        rules.append({"source_id": sid_, "text": clause_text.get(sid_, ""), "shown": n, "accepted": a, "dismissed": d_,
                      "dismiss_rate": round(rate, 2), "unclear": d_ >= 2 and rate >= 0.5, "reasons": reasons[sid_][:3]})
    first = [len(v[0]["findings"]) for v in docs.values()]
    last = [len(v[-1]["findings"]) for v in docs.values() if v[-1]["status"] == "approved"]
    return {"documents": len(docs), "versions": len(rows),
            "approved": sum(1 for v in docs.values() if v[-1]["status"] == "approved"),
            "in_review": sum(1 for v in docs.values() if v[-1]["status"] == "in_review"),
            "avg_first": round(sum(first) / len(first), 1) if first else 0,
            "avg_approved": round(sum(last) / len(last), 1) if last else 0,
            "categories": dict(by_cat), "rules": rules}

@app.get("/")
def index(): return FileResponse(os.path.join(STATIC, "index.html"))
app.mount("/static", StaticFiles(directory=STATIC), name="static")
