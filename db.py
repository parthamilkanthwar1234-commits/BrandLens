import json, os, sqlite3, time
from contextlib import contextmanager

DB_PATH = os.getenv("BRANDLENS_DB", os.path.join(os.path.dirname(__file__), "..", "brandlens.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER NOT NULL, version INTEGER NOT NULL,
  title TEXT, channel TEXT, author TEXT, text TEXT, req_json TEXT, findings_json TEXT,
  actions_json TEXT DEFAULT '{}', signoffs_json TEXT DEFAULT '{}', status TEXT DEFAULT 'draft', created_at REAL);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, submission_id INTEGER, at REAL, actor TEXT, role TEXT, kind TEXT, detail TEXT);
"""

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init():
    with conn() as c:
        c.executescript(SCHEMA)

def row(r):
    if r is None: return None
    d = dict(r)
    for k in ("req_json", "findings_json", "actions_json", "signoffs_json"):
        if k in d: d[k[:-5]] = json.loads(d.pop(k) or "{}")
    return d

def add_event(c, doc_id, sub_id, actor, role, kind, detail="", at=None):
    c.execute("INSERT INTO events(doc_id,submission_id,at,actor,role,kind,detail) VALUES(?,?,?,?,?,?,?)",
              (doc_id, sub_id, at or time.time(), actor, role, kind, detail))
