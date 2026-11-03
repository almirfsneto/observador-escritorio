"""Gera eventos totalmente ficticios de uma microtarefa repetida."""
from datetime import datetime, timezone, timedelta
from uuid import uuid5, NAMESPACE_DNS
from .events import Event

STEPS = [
  ("Chrome", "browser_action", "open", "email_message"),
  ("Chrome", "browser_action", "click", "download_attachment"),
  ("Explorer", "file_action", "open", "downloads_folder"),
  ("Explorer", "file_action", "rename", "example_document"),
  ("Explorer", "file_action", "move", "example_case_folder"),
  ("SistemaDemo", "ui_action", "save", "example_registration"),
]

def generate_sample(repetitions: int = 6) -> list[Event]:
    result = []
    start = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    for i in range(repetitions):
        session_id = str(uuid5(NAMESPACE_DNS, f"session-{i}"))
        for j,(app, typ, action, target) in enumerate(STEPS):
            when = start + timedelta(minutes=20*i, seconds=15*j)
            event = Event(
                schema_version=1, event_id=str(uuid5(NAMESPACE_DNS, f"event-{i}-{j}")),
                timestamp_utc=when.isoformat().replace("+00:00", "Z"),
                device_id="demo-device-01", session_id=session_id, app=app,
                event_type=typ, action=action, target=target, duration_ms=500,
                metadata={"category":"demo"})
            event.validate()
            result.append(event)
    return result
