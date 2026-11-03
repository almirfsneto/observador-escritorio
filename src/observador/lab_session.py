"""Explicitly initiated, short-lived laboratory policy for a synthetic Windows app."""
from datetime import datetime, time, timedelta
from pathlib import Path, PureWindowsPath

from .collector import Application, Policy

LAB_DURATION_MINUTES = 15
SYNTHETIC_BINARY_NAME = "SyntheticTaskApp.exe"


def fixture_path() -> Path:
    """Fixed source-tree path; this laboratory runner is not an installed agent."""
    return (Path(__file__).resolve().parents[2] / "tools" / "SyntheticTaskApp"
            / "bin" / "Release" / "net8.0-windows" / SYNTHETIC_BINARY_NAME)


def validate_lab_executable(executable: str) -> None:
    path = PureWindowsPath(executable)
    if not path.is_absolute() or path.name.casefold() != SYNTHETIC_BINARY_NAME.casefold():
        raise ValueError("laboratory requires a dedicated SyntheticTaskApp.exe")


def make_lab_policy(executable: str, now: datetime) -> Policy:
    """Never enable collection for a generic desktop executable."""
    validate_lab_executable(executable)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware time required")
    return Policy(
        applications=(Application(executable, "synthetic-app"),),
        starts_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=LAB_DURATION_MINUTES),
        work_start=time.min,
        work_end=time.max,
        laboratory_enabled=True,
    )
