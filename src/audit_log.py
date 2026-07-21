import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    received_at TEXT NOT NULL,
    sender TEXT,
    subject TEXT,
    alarm_id TEXT,
    site TEXT,
    machine TEXT,
    metric TEXT,
    severity TEXT,
    reading_value TEXT,
    parsed_ok INTEGER NOT NULL DEFAULT 0,
    parse_error TEXT,
    matched_customer TEXT,
    email_sent INTEGER NOT NULL DEFAULT 0,
    email_error TEXT,
    sms_sent INTEGER NOT NULL DEFAULT 0,
    sms_error TEXT,
    updated_at TEXT NOT NULL
);
"""


class AuditLog:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        with self._connect() as conn:
            conn.execute(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def already_processed(self, message_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE message_id = ?", (message_id,)
            ).fetchone()
            return row is not None

    def record_received(self, message_id: str, sender: str, subject: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO alerts
                   (message_id, received_at, sender, subject, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (message_id, now, sender, subject, now),
            )

    def record_parsed(self, message_id: str, fields: dict | None, error: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            if fields:
                conn.execute(
                    """UPDATE alerts SET parsed_ok = 1, alarm_id = ?, site = ?, machine = ?,
                       metric = ?, severity = ?, reading_value = ?, updated_at = ? WHERE message_id = ?""",
                    (
                        fields.get("alarm_id"),
                        fields.get("site"),
                        fields.get("machine"),
                        fields.get("metric"),
                        fields.get("severity"),
                        fields.get("reading_value"),
                        now,
                        message_id,
                    ),
                )
            else:
                conn.execute(
                    "UPDATE alerts SET parsed_ok = 0, parse_error = ?, updated_at = ? WHERE message_id = ?",
                    (error, now, message_id),
                )

    def record_match(self, message_id: str, customer: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET matched_customer = ?, updated_at = ? WHERE message_id = ?",
                (customer, now, message_id),
            )

    def record_email_result(self, message_id: str, sent: bool, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET email_sent = ?, email_error = ?, updated_at = ? WHERE message_id = ?",
                (1 if sent else 0, error, now, message_id),
            )

    def record_sms_result(self, message_id: str, sent: bool, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET sms_sent = ?, sms_error = ?, updated_at = ? WHERE message_id = ?",
                (1 if sent else 0, error, now, message_id),
            )
