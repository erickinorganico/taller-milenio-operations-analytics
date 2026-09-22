"""Transactional SQLite document store with relational links and audit chain."""
import hashlib
import json
import sqlite3
import threading
from pathlib import Path

from .contracts import FIELDS, DEMO_NOW


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path=":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
          type TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
          document TEXT NOT NULL CHECK(json_valid(document)), PRIMARY KEY(type,id));
        CREATE TABLE IF NOT EXISTS links (
          source_type TEXT NOT NULL, source_id TEXT NOT NULL, field TEXT NOT NULL,
          target_type TEXT NOT NULL, target_id TEXT NOT NULL,
          PRIMARY KEY(source_type,source_id,field),
          FOREIGN KEY(source_type,source_id) REFERENCES entities(type,id) DEFERRABLE INITIALLY DEFERRED,
          FOREIGN KEY(target_type,target_id) REFERENCES entities(type,id) DEFERRABLE INITIALLY DEFERRED);
        CREATE TABLE IF NOT EXISTS events (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, document TEXT NOT NULL, hash TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
          BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
          BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
        CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO settings VALUES ('schema_version','1');
        INSERT OR IGNORE INTO settings VALUES ('mode','demo');
        """)
        if self.db.execute("SELECT value FROM settings WHERE key='schema_version'").fetchone()[0] != "1":
            raise ValueError("Unsupported database schema version")

    def close(self):
        self.db.close()

    def data(self):
        with self.lock:
            out = {kind: [] for kind in FIELDS}
            for row in self.db.execute("SELECT type,document FROM entities ORDER BY type,id"):
                out[row["type"]].append(json.loads(row["document"]))
            return out

    def get(self, kind, entity_id):
        row = self.db.execute("SELECT document FROM entities WHERE type=? AND id=?", (kind, entity_id)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, kind, record, actor, action):
        before = self.get(kind, record["id"])
        self.db.execute("INSERT INTO entities VALUES (?,?,?,?) ON CONFLICT(type,id) DO UPDATE SET version=excluded.version,document=excluded.document",
                        (kind, record["id"], record["version"], canonical(record)))
        self.db.execute("DELETE FROM links WHERE source_type=? AND source_id=?", (kind, record["id"]))
        for field, typ in FIELDS[kind].items():
            if typ.startswith("ref:") and record.get(field):
                self.db.execute("INSERT INTO links VALUES (?,?,?,?,?)", (kind, record["id"], field, typ[4:].rstrip("?"), record[field]))
        last = self.db.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        event = {"seq": last[0] + 1 if last else 1, "at": record["updated_at"], "actor": actor,
                 "action": action, "entity_type": kind, "entity_id": record["id"],
                 "before": before, "after": record, "previous_hash": last[1] if last else "0" * 64}
        self.db.execute("INSERT INTO events(document,hash) VALUES (?,?)", (canonical(event), digest(event)))

    def revision(self):
        return self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]

    def audit(self, limit=100):
        rows = self.db.execute("SELECT document,hash FROM events ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        return [dict(json.loads(row[0]), hash=row[1]) for row in rows]

    def verify_audit(self):
        previous = "0" * 64
        latest = {}
        for row in self.db.execute("SELECT seq,document,hash FROM events ORDER BY seq"):
            event = json.loads(row[1])
            if event["seq"] != row[0] or event["previous_hash"] != previous or digest(event) != row[2]:
                return False
            key = (event["entity_type"], event["entity_id"])
            if event["before"] != latest.get(key):
                return False
            latest[key] = event["after"]
            previous = row[2]
        current = {(r["type"], r["id"]): json.loads(r["document"]) for r in self.db.execute("SELECT * FROM entities")}
        return current == latest

    def initialize(self, fixture):
        from .domain import validate_dataset
        with self.lock:
            if self.revision() or self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]:
                raise ValueError("Database already initialized; use a new demo database")
            validate_dataset(fixture)
            self.db.execute("BEGIN IMMEDIATE")
            try:
                for kind, records in fixture.items():
                    for record in records:
                        self.save(kind, record, "Synthetic fixture", "seed")
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def backup(self, target):
        destination = Path(target)
        if destination.exists():
            raise ValueError("Backup target already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, sqlite3.connect(destination) as other:
            self.db.backup(other)
