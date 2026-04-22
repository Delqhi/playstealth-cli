"""Ban Risk Monitor for calculating risk scores from telemetry."""
import json
from pathlib import Path
from .telemetry import TELEMETRY_FILE

def calculate_ban_risk(session_id: str = None) -> dict:
    """Calculate ban risk score from telemetry data."""
    if not TELEMETRY_FILE.exists():
        return {"risk": 0.0, "status": "no_data"}
    
    events = []
    with open(TELEMETRY_FILE) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    if session_id:
        events = [e for e in events if e.get("sid") == session_id]
    
    total_steps = sum(1 for e in events if e["evt"] == "step_end")
    disqualifications = sum(1 for e in events if e["evt"] == "disqualified")
    traps_hit = sum(1 for e in events if e.get("trap"))
    fast_steps = sum(1 for e in events if e["evt"] == "step_end" and (e.get("dur_ms") or 9999) < 3000)
    
    if total_steps == 0:
        return {"risk": 0.0, "status": "no_steps"}
    
    # Gewichtung: Disqualifikationen & Speed sind kritisch
    risk = (
        (disqualifications / max(total_steps, 1)) * 0.4 +
        (fast_steps / max(total_steps, 1)) * 0.3 +
        (traps_hit / max(total_steps, 1)) * 0.3
    ) * 100
    
    status = "safe" if risk < 15 else ("warning" if risk < 30 else "critical")
    return {
        "risk": round(risk, 1), 
        "status": status, 
        "disqualifications": disqualifications, 
        "fast_steps": fast_steps, 
        "traps": traps_hit
    }
