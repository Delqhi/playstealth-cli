"""Metrics & Telemetry Modul für PlayStealth CLI.

Loggt Success-Rates, Step-Times und Trap-Hits anonymisiert im JSONL-Format.
Keine URLs, keine Fragetexte, keine Antworten. Nur Metriken.
"""
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

TELEMETRY_DIR = Path(os.getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"))
TELEMETRY_FILE = TELEMETRY_DIR / "telemetry.jsonl"


def _ensure_dir():
    """Stellt sicher, dass das Telemetry-Verzeichnis existiert."""
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


def generate_session_id() -> str:
    """Erzeugt eine ephemere, anonymisierte Session-ID."""
    return uuid.uuid4().hex[:12]


def log_event(
    session_id: str,
    event: str,
    platform: str = "unknown",
    step_index: Optional[int] = None,
    duration_ms: Optional[float] = None,
    success: Optional[bool] = None,
    trap_type: Optional[str] = None,
    error_code: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Append-only JSONL Log. POSIX-atomic für Lines < 4KB.
    
    Args:
        session_id: Anonymisierte Session-ID
        event: Event-Typ (step_start, step_end, trap_hit, etc.)
        platform: Name der Survey-Plattform
        step_index: Aktueller Schritt-Index
        duration_ms: Dauer des Events in Millisekunden
        success: Ob der Schritt erfolgreich war
        trap_type: Typ der erkannten Falle (attention_check, honeypot, etc.)
        error_code: Fehlercode bei Misserfolg
        metadata: Zusätzliche Metadaten (optional)
    """
    _ensure_dir()
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sid": session_id,
        "evt": event,
        "plat": platform,
        "step": step_index,
        "dur_ms": round(duration_ms, 1) if duration_ms else None,
        "ok": success,
        "trap": trap_type,
        "err": error_code,
        "meta": metadata or {}
    }
    with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_summary() -> Dict[str, Any]:
    """
    Berechnet aggregierte Metriken aus dem JSONL-Log.
    
    Returns:
        Dictionary mit zusammengefassten Metriken
    """
    if not TELEMETRY_FILE.exists():
        return {"status": "empty", "msg": "No telemetry data recorded yet."}

    events = []
    with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    if not events:
        return {"status": "empty"}

    total_steps = sum(1 for e in events if e["evt"] == "step_end")
    successful_steps = sum(1 for e in events if e["evt"] == "step_end" and e.get("ok") is True)
    trap_hits = sum(1 for e in events if e.get("trap"))
    errors = sum(1 for e in events if e.get("err"))
    durations = [e["dur_ms"] for e in events if e.get("dur_ms") is not None]
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    return {
        "status": "ok",
        "total_events": len(events),
        "steps_completed": total_steps,
        "success_rate": round((successful_steps / total_steps * 100) if total_steps > 0 else 0.0, 1),
        "avg_step_time_ms": round(avg_dur, 1),
        "trap_hits": trap_hits,
        "errors": errors,
        "telemetry_file": str(TELEMETRY_FILE)
    }


def clear_telemetry():
    """Löscht alle Telemetry-Daten (für Testing oder Privacy)."""
    if TELEMETRY_FILE.exists():
        TELEMETRY_FILE.unlink()
        return {"status": "cleared", "file": str(TELEMETRY_FILE)}
    return {"status": "nothing_to_clear"}
