"""Contrato versionado para eventos de tarefas: sem conteudos sensiveis."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
import math

ALLOWED_TYPES = frozenset({
    "session_start", "session_end", "window_focus", "ui_action", "file_action",
    "browser_action", "error", "screenshot"
})
ALLOWED_META = frozenset({"control_role", "http_status", "result", "confidence", "category", "source_sequence"})

@dataclass(frozen=True)
class Event:
    schema_version: int
    event_id: str
    timestamp_utc: str
    device_id: str
    session_id: str
    app: str
    event_type: str
    action: str
    target: str
    duration_ms: int = 0
    screenshot_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        for name in ("event_id", "session_id"):
            UUID(getattr(self, name))
        dt = datetime.fromisoformat(self.timestamp_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
            raise ValueError("timestamp_utc must have UTC timezone")
        if self.event_type not in ALLOWED_TYPES:
            raise ValueError("invalid event type")
        if type(self.duration_ms) is not int or self.duration_ms < 0:
            raise ValueError("duration_ms must be nonnegative")
        for name in ("device_id", "app", "action", "target"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v or len(v) > 160:
                raise ValueError(f"invalid {name}")
        if not isinstance(self.metadata, dict) or set(self.metadata) - ALLOWED_META:
            raise ValueError("metadata contains unapproved keys")
        for key, value in self.metadata.items():
            if key == "confidence":
                valid = type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
            elif key == "http_status":
                valid = type(value) is int and 100 <= value <= 599
            elif key == "source_sequence":
                valid = type(value) is int and 0 < value < 2**63
            elif key == "result":
                valid = value in ("success", "failure", "cancelled", "unknown")
            elif key == "category":
                valid = value in ("demo", "laboratory", "synthetic")
            else:
                valid = value in ("button", "checkbox", "combobox", "edit", "listitem",
                                  "menuitem", "tab", "window", "control")
            if not valid:
                raise ValueError("metadata value outside approved domain")
        if self.screenshot_ref is not None:
            if (not isinstance(self.screenshot_ref, str) or not self.screenshot_ref
                    or "\\" in self.screenshot_ref or ":" in self.screenshot_ref
                    or any(part in ("", ".", "..") for part in self.screenshot_ref.split("/"))):
                raise ValueError("screenshot_ref must be safe relative path")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        event = cls(**data)
        event.validate()
        return event

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
