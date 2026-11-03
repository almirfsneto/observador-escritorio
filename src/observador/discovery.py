"""Detector inicial de microtarefas em sequencias ficticias.

Nao e Process Mining completo. Nao comprova causalidade.
"""
from collections import defaultdict
from datetime import datetime
from statistics import median
from .events import Event

def _timestamp(e: Event) -> float:
    return datetime.fromisoformat(e.timestamp_utc.replace("Z", "+00:00")).timestamp()

def discover_patterns(events: list[Event], min_count: int = 2, min_steps: int = 2,
                      max_steps: int = 6, max_gap_seconds: int = 120) -> list[dict]:
    """Descobre n-gramas contiguos, separados por dispositivo/sessao e lacuna de tempo."""
    sessions: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for ev in events:
        ev.validate()
        if ev.event_type in {"ui_action", "file_action", "browser_action"}:
            sessions[(ev.device_id, ev.session_id)].append(ev)
    candidates: dict[tuple, list[float]] = defaultdict(list)
    for group in sessions.values():
        group.sort(key=lambda e: (_timestamp(e), e.event_id))
        for i in range(len(group)):
            for n in range(min_steps, max_steps + 1):
                segment = group[i:i+n]
                if len(segment) != n:
                    continue
                times = [_timestamp(e) for e in segment]
                if any(b-a > max_gap_seconds for a,b in zip(times,times[1:])):
                    continue
                fingerprint = tuple((e.app, e.event_type, e.action, e.target) for e in segment)
                duration = max(0.0, times[-1] - times[0]) + segment[-1].duration_ms / 1000
                candidates[fingerprint].append(duration)
    result = []
    for fp, durations in candidates.items():
        if len(durations) >= min_count:
            result.append({
                "steps": [{"app": a, "event_type": t, "action": c, "target": v} for a,t,c,v in fp],
                "occurrences": len(durations),
                "median_duration_seconds": round(median(durations), 2),
                "confidence_note": "Padrao temporal candidato; requer revisao humana",
            })
    result.sort(key=lambda p: (-len(p["steps"]), -p["occurrences"], p["median_duration_seconds"]))
    return result
