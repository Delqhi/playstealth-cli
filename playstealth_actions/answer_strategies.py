"""Survey Answer Strategies Module.

Steuert Antwortmuster pro Session. Vollständig deterministisch bei `persona`,
zufällig bei `random`, stabil bei `consistent`.
"""
import random
import hashlib
from abc import ABC, abstractmethod
from typing import List, Union, Optional


class BaseStrategy(ABC):
    """Basis-Klasse für alle Antwort-Strategien."""
    
    @abstractmethod
    async def choose(self, question: str, option_count: int, options: List[str]) -> Union[int, str]:
        """Gibt Index oder Text der zu wählenden Option zurück."""
        pass


class RandomStrategy(BaseStrategy):
    """Wählt Antworten komplett zufällig."""
    
    async def choose(self, question: str, option_count: int, options: List[str]) -> Union[int, str]:
        if option_count == 0:
            return 0
        return random.randint(0, option_count - 1)


class ConsistentStrategy(BaseStrategy):
    """Wählt immer denselben Index (z.B. immer die zweite Option)."""
    
    def __init__(self, fixed_index: int = 1):
        self.fixed_index = fixed_index

    async def choose(self, question: str, option_count: int, options: List[str]) -> Union[int, str]:
        if option_count == 0:
            return 0
        return min(self.fixed_index, max(0, option_count - 1))


class PersonaStrategy(BaseStrategy):
    """Wählt basierend auf einem Profil (optimistic, critical, neutral).
    
    Deterministisch pro Frage (gleiche Frage = gleiche Antwort),
    aber gewichtet nach Persona-Profil.
    """
    
    def __init__(self, persona: str = "neutral"):
        self.persona = persona
        self.weights = {
            "optimistic": [0.45, 0.30, 0.15, 0.07, 0.03],
            "critical":   [0.03, 0.07, 0.15, 0.30, 0.45],
            "neutral":    [0.10, 0.20, 0.40, 0.20, 0.10]
        }.get(persona, [0.2] * 5)

    async def choose(self, question: str, option_count: int, options: List[str]) -> Union[int, str]:
        if option_count == 0:
            return 0
        
        # Seed aus Frage-Text → gleiche Frage = gleiche Antwort (Konsistenz)
        q_hash = int(hashlib.md5(question.encode()).hexdigest(), 16)
        rng = random.Random(q_hash)
        
        # Gewichte auf tatsächliche Optionen zuschneiden
        w = self.weights[:option_count]
        total = sum(w)
        if total == 0:
            return rng.randint(0, option_count - 1)
        
        normalized = [x / total for x in w]
        return rng.choices(range(option_count), weights=normalized, k=1)[0]


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """Factory-Funktion zum Erstellen einer Strategie-Instanz.
    
    Args:
        name: Name der Strategie ('random', 'consistent', 'persona')
        **kwargs: Weitere Argumente für die Strategie (z.B. persona='optimistic')
    
    Returns:
        Instanz der gewünschten Strategie
    
    Raises:
        ValueError: Wenn unbekannter Strategie-Name
    """
    strategies = {
        "random": RandomStrategy,
        "consistent": ConsistentStrategy,
        "persona": PersonaStrategy
    }
    
    cls = strategies.get(name)
    if not cls:
        raise ValueError(f"❌ Unknown strategy: {name}. Available: {list(strategies.keys())}")
    
    return cls(**kwargs)
