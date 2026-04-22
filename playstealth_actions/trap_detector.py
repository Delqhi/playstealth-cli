import re
from playwright.async_api import Page
from typing import Dict, Any, List, Optional


async def detect_honeypots(page: Page) -> List[Dict[str, Any]]:
    """Findet DOM-Elemente, die typische Honeypot-Muster aufweisen."""
    js = """
    () => {
        const traps = [];
        const els = document.querySelectorAll('input, textarea, select, button, [role="button"], [role="checkbox"], [role="radio"]');
        els.forEach(el => {
            const style = window.getComputedStyle(el);
            const isHidden = style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0;
            const isOffscreen = el.offsetLeft < -9000 || el.offsetTop < -9000;
            const isTypeHidden = el.type === 'hidden';
            const hasTrapName = /hp|honeypot|bot|trap|hidden|invisible|check_human/i.test(el.name || '');
            const hasTrapClass = /hp|honeypot|bot|trap|hidden|invisible/i.test(el.className || '');
            const hasTrapId = /hp|honeypot|bot|trap|hidden|invisible/i.test(el.id || '');
            
            if (isHidden || isOffscreen || isTypeHidden || hasTrapName || hasTrapClass || hasTrapId) {
                traps.push({
                    tag: el.tagName,
                    type: el.type || null,
                    name: el.name || null,
                    id: el.id || null,
                    className: el.className || null,
                    reason: isTypeHidden ? 'type_hidden' : (isHidden ? 'css_hidden' : (isOffscreen ? 'offscreen' : 'naming_pattern'))
                });
            }
        });
        return traps;
    }
    """
    return await page.evaluate(js)


def parse_attention_check(question_text: str, options: List[str]) -> Optional[Dict[str, Any]]:
    """Parst Fragetext auf explizite Instruktionen und matched sie gegen Optionen."""
    if not question_text or not options:
        return None

    text_lower = question_text.lower()
    
    # Muster für explizite Auswahl-Instruktionen (DE/EN)
    patterns = [
        r"(?:wähle|select|click|choose|mark|pick|klicke)\s+(?:die|the|option)?\s*['\"]?([^'\".]+)['\"]?",
        r"(?:bitte|please)\s+(?:wählen|select|choose|antworten)\s+(?:sie|you)?\s*['\"]?([^'\".]+)['\"]?",
        r"(?:antwort|answer)\s+(?:mit|with)\s+['\"]?([^'\".]+)['\"]?",
        r"(?:dritte|third|zweite|second|erste|first|vierte|fourth|fünfte|fifth|letzte|last)\s+(?:option|antwort|choice|kästchen)",
        r"(?:stimme|agree|disagree)\s+(?:nicht|strongly|somewhat|voll|gar)\s+(?:zu|nicht zu)",
    ]

    for pat in patterns:
        match = re.search(pat, text_lower)
        if match:
            instruction = match.group(0).strip()
            target = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else ""
            
            # Index-basierte Instruktion (z.B. "dritte Option")
            index_match = re.search(r"(erste|zweite|dritte|vierte|fünfte|first|second|third|fourth|fifth)", text_lower)
            if index_match:
                idx_map = {"erste": 0, "first": 0, "zweite": 1, "second": 1, "dritte": 2, "third": 2, "vierte": 3, "fourth": 3, "fünfte": 4, "fifth": 4}
                idx = idx_map.get(index_match.group(1))
                if idx is not None and idx < len(options):
                    return {"type": "attention_check", "action": "select_index", "index": idx, "instruction": instruction}

            # Text-basierter Match
            for i, opt in enumerate(options):
                opt_clean = re.sub(r'<[^>]+>', '', opt).lower().strip()
                if target and (target in opt_clean or opt_clean in target):
                    return {"type": "attention_check", "action": "select_index", "index": i, "instruction": instruction}
            
            return {"type": "attention_check", "action": "manual_review", "instruction": instruction}
            
    return None


async def analyze_page_traps(page: Page, question_text: str, options: List[str]) -> Dict[str, Any]:
    """Kombinierte Analyse für Plugins. Gibt klare Handlungsempfehlung zurück."""
    honeypots = await detect_honeypots(page)
    attention = parse_attention_check(question_text, options)
    
    is_safe = len(honeypots) == 0 and attention is None
    recommendation = "proceed" if is_safe else "handle_traps"
    
    return {
        "honeypots": honeypots,
        "attention_check": attention,
        "is_safe": is_safe,
        "recommendation": recommendation
    }
