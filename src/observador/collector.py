"""Fail-closed collection policy and projection; no background service is started."""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import PureWindowsPath
from typing import Callable, Protocol
from uuid import uuid4

from .events import Event


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone required")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Application:
    executable: str
    alias: str

    def __post_init__(self):
        if not PureWindowsPath(self.executable).is_absolute():
            raise ValueError("absolute Windows executable path required")
        if not self.alias.isascii() or not self.alias.replace("-", "").isalnum():
            raise ValueError("use a synthetic application alias")
        if len(self.alias) > 80:
            raise ValueError("alias too long")


@dataclass(frozen=True)
class Policy:
    applications: tuple[Application, ...]
    starts_at: datetime
    expires_at: datetime
    # Hours use the timezone of the clock supplied by the caller, not host UTC.
    work_start: time = time(9)
    work_end: time = time(18)
    laboratory_enabled: bool = False

    def __post_init__(self):
        if utc(self.starts_at) >= utc(self.expires_at):
            raise ValueError("invalid observation interval")
        if self.work_start.tzinfo or self.work_end.tzinfo or self.work_start >= self.work_end:
            raise ValueError("use a same-day local working interval")
        paths = [a.executable.casefold() for a in self.applications]
        aliases = [a.alias for a in self.applications]
        if len(set(paths)) != len(paths) or len(set(aliases)) != len(aliases):
            raise ValueError("duplicate application")

    def permits(self, now: datetime) -> bool:
        instant = utc(now)
        return (self.laboratory_enabled and bool(self.applications)
                and utc(self.starts_at) <= instant < utc(self.expires_at)
                and self.work_start <= now.time().replace(tzinfo=None) < self.work_end)


@dataclass(frozen=True)
class Observation:
    application_index: int
    control_type: int
    is_password: bool


class Backend(Protocol):
    def observe(self, applications: tuple[Application, ...]) -> Observation | None: ...


# Numeric UIA control IDs. Dynamic names/automation IDs/values are never read.
ROLES = {50000: "button", 50002: "checkbox", 50003: "combobox",
         50004: "edit", 50007: "listitem", 50011: "menuitem",
         50018: "tab", 50032: "window"}


class Collector:
    def __init__(self, policy: Policy, backend: Backend, device_id: str,
                 clock: Callable[[], datetime] = lambda: datetime.now().astimezone()):
        self.policy, self.backend, self.device_id = policy, backend, device_id
        self.clock = clock
        self.session_id = str(uuid4())
        self.paused = False
        self.stopped = False
        self.health = "idle"
        self._previous = None

    def pause(self):
        self.paused = True
        self._previous = None
        self.health = "paused"

    def resume(self):
        if not self.stopped:
            self.paused = False

    def stop(self):
        self.stopped = True
        self._previous = None
        self.health = "stopped"

    def poll(self) -> Event | None:
        now = self.clock()
        if utc(now) >= utc(self.policy.expires_at):
            self.stop()
        if self.stopped or self.paused or not self.policy.permits(now):
            self._previous = None
            if not self.stopped and not self.paused:
                self.health = "disabled"
            return None
        try:
            observation = self.backend.observe(self.policy.applications)
            now = self.clock()
            if utc(now) >= utc(self.policy.expires_at):
                self.stop()
            if self.stopped or self.paused or not self.policy.permits(now):
                self._previous = None
                if not self.stopped and not self.paused:
                    self.health = "disabled"
                return None
            if observation is None or observation.is_password:
                self._previous = None
                self.health = "excluded"
                return None
            index = observation.application_index
            if type(index) is not int or not 0 <= index < len(self.policy.applications):
                raise ValueError("invalid application index")
            if type(observation.is_password) is not bool or type(observation.control_type) is not int:
                raise ValueError("invalid observation")
            role = ROLES.get(observation.control_type, "control")
            # A focus change is not evidence of a click or text input.
            signature = (index, role)
            self.health = "active"
            if signature == self._previous:
                return None
            event = Event(1, str(uuid4()), utc(now).isoformat(), self.device_id,
                          self.session_id, self.policy.applications[index].alias,
                          "window_focus", "focus", role,
                          metadata={"control_role": role, "category": "laboratory"})
            event.validate()
            self._previous = signature
            return event
        except Exception:
            # Exceptions from OS/UIA can contain window titles or paths.
            self.health = "backend_error"
            self._previous = None
            return None
