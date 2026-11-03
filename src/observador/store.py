"""Armazenamento de eventos em SQLite para o prototipo offline."""
import json
import sqlite3
from pathlib import Path
from .events import Event

DDL = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    timestamp_utc TEXT NOT NULL,
    device_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_session_time
ON events(device_id, session_id, timestamp_utc);
"""

class EventStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(DDL)

    def close(self) -> None:
        self.conn.close()

    def insert(self, event: Event) -> bool:
        payload = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            c = self.conn.execute("""INSERT OR IGNORE INTO events
                (event_id, timestamp_utc, device_id, session_id, event_type, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (event.event_id, event.timestamp_utc, event.device_id, event.session_id, event.event_type, payload))
        return c.rowcount == 1

    def list_events(self) -> list[Event]:
        rows = self.conn.execute("""SELECT payload_json FROM events
            ORDER BY timestamp_utc, event_id""").fetchall()
        return [Event.from_dict(json.loads(row[0])) for row in rows]

    def export_jsonl(self, path: str | Path) -> int:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        events = self.list_events()
        with dest.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return len(events)
