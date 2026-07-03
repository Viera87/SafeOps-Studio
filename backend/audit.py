from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from models import AuditEvent, Role

DB_PATH = Path(__file__).with_name("audit.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            role TEXT NOT NULL,
            script_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            inputs TEXT NOT NULL,
            exit_code INTEGER,
            output_excerpt TEXT NOT NULL
        )
        """
    )
    return conn


def record_event(
    *,
    user: str,
    role: Role,
    script_id: str,
    action: str,
    status: str,
    inputs: dict,
    exit_code: int | None = None,
    output: str = "",
) -> AuditEvent:
    event = AuditEvent(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        user=user,
        role=role,
        script_id=script_id,
        action=action,
        status=status,
        inputs=inputs,
        exit_code=exit_code,
        output_excerpt=output[:1000],
    )
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_events
            (id, timestamp, user, role, script_id, action, status, inputs, exit_code, output_excerpt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.timestamp.isoformat(),
                event.user,
                event.role.value,
                event.script_id,
                event.action,
                event.status,
                json.dumps(event.inputs, sort_keys=True),
                event.exit_code,
                event.output_excerpt,
            ),
        )
    return event


def list_events(limit: int = 50) -> list[AuditEvent]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, user, role, script_id, action, status, inputs, exit_code, output_excerpt
            FROM audit_events
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        AuditEvent(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            user=row[2],
            role=Role(row[3]),
            script_id=row[4],
            action=row[5],
            status=row[6],
            inputs=json.loads(row[7]),
            exit_code=row[8],
            output_excerpt=row[9],
        )
        for row in rows
    ]
