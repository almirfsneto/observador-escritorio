"""Experimental one-shot Windows UIA bridge. No hooks, values, or screenshots."""
import json
import os
from pathlib import Path
import subprocess
import sys

from .collector import Application, Observation


class WindowsBackend:
    def observe(self, applications: tuple[Application, ...]) -> Observation | None:
        if not applications:
            return None
        if sys.platform != "win32":
            raise OSError("Windows required")
        # Use the system executable, without shell interpolation or PATH lookup.
        executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        result = subprocess.run(
            [str(executable), "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
             str(Path(__file__).with_name("windows_probe.ps1"))],
            input=json.dumps([a.executable for a in applications]),
            text=True, encoding="utf-8", capture_output=True, timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise OSError("Windows probe failed")
        data = json.loads(result.stdout.lstrip("\ufeff"))
        if data is None:
            return None
        if (not isinstance(data, dict) or set(data) != {"index", "role", "password"}
                or type(data["index"]) is not int or type(data["role"]) is not int
                or type(data["password"]) is not bool):
            raise ValueError("invalid probe response")
        return Observation(data["index"], data["role"], data["password"])
