import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/pm_os.db")

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'backlog',
            priority TEXT DEFAULT 'medium',
            owner TEXT,
            quarter TEXT,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS standups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            raw_notes TEXT,
            done TEXT,
            doing TEXT,
            blocked TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS prds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id INTEGER,
            title TEXT NOT NULL,
            problem TEXT,
            goals TEXT,
            user_stories TEXT,
            edge_cases TEXT,
            metrics TEXT,
            full_draft TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            agent TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

# --- Features ---
def add_feature(title, description="", status="backlog", priority="medium", owner="", quarter="", tags=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO features (title, description, status, priority, owner, quarter, tags) VALUES (?,?,?,?,?,?,?)",
        (title, description, status, priority, owner, quarter, tags)
    )
    conn.commit()
    conn.close()

def get_features(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM features WHERE status=? ORDER BY priority DESC, updated_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM features ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_feature(feature_id, **kwargs):
    kwargs["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [feature_id]
    conn = get_conn()
    conn.execute(f"UPDATE features SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()

def delete_feature(feature_id):
    conn = get_conn()
    conn.execute("DELETE FROM features WHERE id=?", (feature_id,))
    conn.commit()
    conn.close()

# --- Standups ---
def save_standup(date, raw_notes, done, doing, blocked):
    conn = get_conn()
    conn.execute(
        "INSERT INTO standups (date, raw_notes, done, doing, blocked) VALUES (?,?,?,?,?)",
        (date, raw_notes, done, doing, blocked)
    )
    conn.commit()
    conn.close()

def get_standups(limit=10):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM standups ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- PRDs ---
def save_prd(title, full_draft, feature_id=None, problem="", goals="", user_stories="", edge_cases="", metrics=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO prds (feature_id, title, problem, goals, user_stories, edge_cases, metrics, full_draft) VALUES (?,?,?,?,?,?,?,?)",
        (feature_id, title, problem, goals, user_stories, edge_cases, metrics, full_draft)
    )
    conn.commit()
    conn.close()

def get_prds(limit=10):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM prds ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Chat history ---
def save_message(role, content, agent=None):
    conn = get_conn()
    conn.execute("INSERT INTO chat_history (role, content, agent) VALUES (?,?,?)", (role, content, agent))
    conn.commit()
    conn.close()

def get_chat_history(limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))

def get_roadmap_summary():
    conn = get_conn()
    features = conn.execute("SELECT status, COUNT(*) as count FROM features GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["count"] for r in features}
