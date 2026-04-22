"""Persona Manager for consistent demographic profiles across surveys."""
import json
import hashlib
import random
from pathlib import Path
from typing import Dict, Any, Optional

PERSONA_DIR = Path(__import__("os").getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"))
PERSONA_FILE = PERSONA_DIR / "personas.json"

DEFAULT_PERSONA = {
    "age": 34, 
    "gender": "male", 
    "country": "DE", 
    "city": "Berlin",
    "income_bracket": "3000-4000", 
    "education": "Bachelor", 
    "employment": "Full-time",
    "interests": ["tech", "finance", "travel", "health"], 
    "household_size": 2
}

def load_personas() -> Dict[str, Any]:
    """Load all personas from file."""
    if not PERSONA_FILE.exists():
        return {"default": DEFAULT_PERSONA}
    with open(PERSONA_FILE) as f:
        return json.load(f)

def save_personas(data: Dict[str, Any]):
    """Save personas to file."""
    PERSONA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PERSONA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_persona(name: str = "default") -> Dict[str, Any]:
    """Get persona by name."""
    return load_personas().get(name, DEFAULT_PERSONA)

def create_persona(name: str, **kwargs) -> Dict[str, Any]:
    """Create a new persona."""
    personas = load_personas()
    persona = DEFAULT_PERSONA.copy()
    persona.update(kwargs)
    personas[name] = persona
    save_personas(personas)
    return persona

def answer_screening(question: str, options: list, persona: Dict[str, Any]) -> Optional[int]:
    """Deterministische Screening-Antwort basierend auf Persona + Frage-Hash."""
    q_hash = int(hashlib.md5(question.lower().encode()).hexdigest(), 16)
    rng = random.Random(q_hash)
    
    # Einfache Heuristik: Match Persona-Keywords gegen Optionen
    persona_text = " ".join(str(v) for v in persona.values()).lower()
    matches = []
    for i, opt in enumerate(options):
        opt_clean = opt.lower()
        if any(kw in opt_clean for kw in persona_text.split()):
            matches.append(i)
    
    if matches:
        return rng.choice(matches)
    return rng.randint(0, max(0, len(options)-1))
