"""Consistency Validator for cross-survey answer tracking and straight-line detection."""
import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any

STATE_DIR = Path(__import__("os").getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"))
CONSISTENCY_FILE = STATE_DIR / "consistency_log.json"

DEMOGRAPHIC_KEYWORDS = {
    "age": ["alter", "age", "jahre", "years", "geboren", "born"],
    "income": ["einkommen", "income", "verdienst", "gehalt", "salary", "haushaltseinkommen"],
    "employment": ["beruf", "employment", "arbeit", "job", "tätigkeit", "occupation", "status"],
    "education": ["bildung", "education", "abschluss", "degree", "schule", "studium"],
    "household": ["haushalt", "household", "personen", "kinder", "children", "familie"],
    "location": ["wohnort", "location", "stadt", "city", "bundesland", "state", "plz", "zip"]
}

def _load_log() -> Dict[str, Any]:
    if not CONSISTENCY_FILE.exists():
        return {"history": [], "straight_line_flags": 0, "contradictions": 0}
    with open(CONSISTENCY_FILE, encoding="utf-8") as f:
        return json.load(f)

def _save_log(data: Dict[str, Any]):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONSISTENCY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def record_answer(question: str, answer: str, survey_id: str = "unknown"):
    """Speichert Antwort asynchron (non-blocking)."""
    log = await asyncio.to_thread(_load_log)
    log["history"].append({"q": question[:120], "a": answer[:120], "sid": survey_id})
    if len(log["history"]) > 600:
        log["history"] = log["history"][-500:]
    await asyncio.to_thread(_save_log, log)

async def validate_consistency(question: str, answer: str, persona: Dict[str, Any]) -> Dict[str, Any]:
    """Prüft Antwort auf Widerspruch zur Persona."""
    q_lower = question.lower()
    a_lower = answer.lower()
    contradictions = []

    # Age
    if any(k in q_lower for k in DEMOGRAPHIC_KEYWORDS["age"]):
        nums = re.findall(r'\d+', a_lower)
        if nums:
            ans_age = int(nums[0])
            p_age = persona.get("age")
            if p_age and abs(ans_age - p_age) > 2:
                contradictions.append(f"Age: {ans_age} vs persona {p_age}")

    # Income
    if any(k in q_lower for k in DEMOGRAPHIC_KEYWORDS["income"]):
        p_inc = persona.get("income_bracket", "").lower()
        if p_inc and p_inc not in a_lower and a_lower not in p_inc:
            contradictions.append(f"Income: '{a_lower}' vs '{p_inc}'")

    # Employment
    if any(k in q_lower for k in DEMOGRAPHIC_KEYWORDS["employment"]):
        p_emp = persona.get("employment", "").lower()
        if p_emp and p_emp not in a_lower and a_lower not in p_emp:
            contradictions.append(f"Employment: '{a_lower}' vs '{p_emp}'")

    # Education
    if any(k in q_lower for k in DEMOGRAPHIC_KEYWORDS["education"]):
        p_edu = persona.get("education", "").lower()
        if p_edu and p_edu not in a_lower and a_lower not in p_edu:
            contradictions.append(f"Education: '{a_lower}' vs '{p_edu}'")

    return {"consistent": len(contradictions) == 0, "contradictions": contradictions}

async def detect_straight_lining(recent_answers: List[str], threshold: int = 4) -> bool:
    """Erkennt Straight-Lining in Matrix/Likert-Fragen."""
    if len(recent_answers) < threshold:
        return False
    last_n = recent_answers[-threshold:]
    # Normalisiere Antworten (Index oder Text)
    normalized = [str(a).strip().lower() for a in last_n]
    return len(set(normalized)) == 1
