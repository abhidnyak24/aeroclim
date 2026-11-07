import json
import sqlite3
from pathlib import Path

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=15)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS raw (
          node TEXT, boot TEXT, seq INTEGER, ts REAL, received REAL, source TEXT, payload TEXT,
          PRIMARY KEY(node,boot,seq));
        CREATE INDEX IF NOT EXISTS raw_time ON raw(node,ts);
        CREATE TABLE IF NOT EXISTS buckets (
          node TEXT, ts REAL, source TEXT, payload TEXT, PRIMARY KEY(node,ts));
        CREATE TABLE IF NOT EXISTS results (
          node TEXT, ts REAL, payload TEXT, PRIMARY KEY(node,ts));
        CREATE TABLE IF NOT EXISTS events (ts REAL, kind TEXT, detail TEXT);
        PRAGMA user_version=3;
        ''')
        self.db.commit()

    def insert(self, p):
        cur = self.db.execute('INSERT OR IGNORE INTO raw VALUES (?,?,?,?,?,?,?)',
            (p['node_id'], p['boot_id'], p['seq'], p['timestamp'], p['received'], p['source'], json.dumps(p)))
        self.db.commit()
        return cur.rowcount == 1

    def latest_ts(self, node):
        return self.db.execute('SELECT MAX(ts) FROM raw WHERE node=?', (node,)).fetchone()[0]

    def bucket(self, row, result):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO buckets VALUES (?,?,?,?)',
                (row['node_id'], row['ts'], row['source'], json.dumps(row)))
            self.db.execute('INSERT OR IGNORE INTO results VALUES (?,?,?)',
                (row['node_id'], row['ts'], json.dumps(result)))

    def history(self):
        return [json.loads(x[0]) for x in self.db.execute('SELECT payload FROM buckets ORDER BY ts')]

    def event(self, ts, kind, detail):
        self.db.execute('INSERT INTO events VALUES (?,?,?)', (ts, kind, str(detail)[:300]))
        self.db.commit()

    def close(self):
        self.db.close()
