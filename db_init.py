#Creates tables if they don’t exist (called by both apps).

import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    handle TEXT,
    content TEXT,
    category TEXT,
    stock_name TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS stock_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE
);
"""

def get_conn(db_path="tweets.db"):
    return sqlite3.connect(db_path, check_same_thread=False)

def init_db(conn):
    cur = conn.cursor()
    for stmt in DDL.strip().split(";\n\n"):
        if stmt.strip():
            cur.execute(stmt)
    conn.commit()
