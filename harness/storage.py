"""
Storage
-------
Free, zero-cost persistence using local SQLite. No hosted DB needed.
For the Streamlit Cloud deployment, this file lives in the app's ephemeral
storage per session by default; for a persistent public trust-report across
users, point DB_PATH at a small file committed via a scheduled export, or
swap in a free tier of Supabase/Turso later if you want cross-session
persistence without re-architecting anything else.
"""

import sqlite3
import time
import json
import os

DB_PATH = os.environ.get("REDTEAM_DB_PATH", "redteam_results.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT,
            timestamp REAL,
            target_label TEXT,
            attack_id TEXT,
            category TEXT,
            severity TEXT,
            verdict TEXT,
            matched_signals TEXT,
            raw_response TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS external_users (
            timestamp REAL,
            user_label TEXT,
            target_label TEXT,
            run_id TEXT
        )
    """)
    return conn


def save_result(run_id: str, target_label: str, attack: dict, verdict_obj):
    conn = _connect()
    conn.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
        (
            run_id,
            time.time(),
            target_label,
            attack["id"],
            attack["category"],
            attack.get("severity", "unknown"),
            verdict_obj.verdict,
            json.dumps(verdict_obj.matched_signals),
            verdict_obj.raw_response[:2000],  # cap stored response size
        ),
    )
    conn.commit()
    conn.close()


def log_external_user(user_label: str, target_label: str, run_id: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO external_users VALUES (?,?,?,?)",
        (time.time(), user_label, target_label, run_id),
    )
    conn.commit()
    conn.close()


def summary_stats():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(DISTINCT target_label) FROM runs")
    distinct_agents = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM runs")
    total_attacks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM runs WHERE verdict='succeeded'")
    vulns_found = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT user_label) FROM external_users")
    external_users = cur.fetchone()[0]

    cur.execute("""
        SELECT category, COUNT(*) as c FROM runs
        WHERE verdict='succeeded'
        GROUP BY category ORDER BY c DESC LIMIT 1
    """)
    row = cur.fetchone()
    top_failure_category = row[0] if row else "N/A"

    conn.close()
    return {
        "external_users": external_users,
        "distinct_agents": distinct_agents,
        "total_attack_attempts": total_attacks,
        "vulnerabilities_found": vulns_found,
        "most_common_failure_category": top_failure_category,
    }


def all_results():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM runs ORDER BY timestamp DESC")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows
