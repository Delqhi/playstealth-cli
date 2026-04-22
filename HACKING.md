# HACKING.md - PlayStealth CLI Developer Guide

## 🎯 Die "Weltbeste CLI für Hacker"

PlayStealth ist nicht nur ein Automatisierungsskript – es ist eine **Anti-Detection-Engine** für professionelle Survey-Automatisierung. Dieses Dokument erklärt, wie das Stealth-System funktioniert und wie du neue Survey-Typen hinzufügst.

---

## 📚 Inhaltsverzeichnis

1. [Architektur-Übersicht](#architektur-übersicht)
2. [Human Behavior Engine](#human-behavior-engine)
3. [Stealth Profile System](#stealth-profile-system)
4. [Robuste Selektor-Heuristiken](#robuste-selektor-heuristiken)
5. [Session & State Management](#session--state-management)
6. [Diagnostik & Leak-Tests](#diagnostik--leak-tests)
7. [Neue Survey-Typen hinzufügen](#neue-survey-typen-hinzufügen)
8. [Production Best Practices](#production-best-practices)

---

## 🏗️ Architektur-Übersicht

```
playstealth-cli/
├── playstealth_actions/
│   ├── human_behavior.py      # Human-like interactions (Mauskurven, Delays)
│   ├── stealth_enhancer.py    # Fingerprint protection (WebGL, Canvas, etc.)
│   ├── smart_actions.py       # Multi-strategy selector resolution
│   ├── state_store.py         # Browser context persistence
│   ├── diagnose_benchmark.py  # Automated stealth testing
│   └── tool_registry.py       # Central tool interface
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── mock_pages.py          # Mock HTML for testing
│   └── test_survey_flow.py    # Integration tests
└── HACKING.md                 # Dieses Dokument
```

### Die Vier Säulen der Anti-Detection

| Säule | Modul | Zweck |
|-------|-------|-------|
| **Human Behavior** | `human_behavior.py` | Simuliert natürliche Interaktionen (Maus, Tastatur, Scrollen) |
| **Fingerprint Protection** | `stealth_enhancer.py` | Versteckt Bot-Indikatoren (webdriver, WebGL, Canvas) |
| **Resiliente Selektoren** | `smart_actions.py` | 8-fache Fallback-Hierarchie gegen DOM-Änderungen |
| **State Persistence** | `state_store.py` | Vollständige Browser-Context-Persistenz (Cookies, Storage) |

---

## 🖱️ Human Behavior Engine

### Warum roboterhafte Klicks scheitern

Moderne Bot-Detection analysiert:
- **Mausbewegungen**: Gerade Linien = Bot
- **Klick-Timing**: Exakt 1000ms Pause = Bot
- **Tippverhalten**: Konstante Geschwindigkeit = Bot
- **Scrollen**: Sofortiger Sprung = Bot

### Implementierung

#### Bézier-Kurven für Mausbewegungen

```python
from playstealth_actions.human_behavior import human_click, mouse_move_curve

# Anstatt: await page.click("#button")
await human_click(page, "#button")

# Die Funktion:
# 1. Berechnet kubische Bézier-Kurve mit zufälligen Kontrollpunkten
# 2. Bewegt Maus in 20-30 Schritten entlang der Kurve
# 3. Fügt Mikro-Jitter hinzu (±2px pro Schritt)
# 4. Variiert Geschwindigkeit (6-18ms pro Schritt)
```

#### Gaussian-verteilte Delays

```python
import random
import asyncio

# Schlecht: Feste Wartezeit
await asyncio.sleep(1.0)

# Gut: Gaussian-Verteilung mit Clamp
delay = max(0.1, min(1.5, random.gauss(0.4, 0.15)))
await asyncio.sleep(delay)
```

Die `human_behavior.py`-Module verwenden diese Technik für:
- Pre-Click Hesitation (0.2–0.8s)
- Post-Click Reaction (0.1–0.3s)
- Typing Speed Variation (80ms ± 30ms pro Zeichen)
- Denkpausen (5% Chance auf 0.25–0.7s Pause)

#### Scrollen mit Beschleunigung

```python
from playstealth_actions.human_behavior import human_scroll

# Anstatt: await page.evaluate("window.scrollTo(0, 1000)")
await human_scroll(page, target_y=1000, duration=1.4)

# Verwendet Ease-Out-Kurve: 1 - (1 - t)³
# Simuliert natürliches Abbremsen am Ende
```

### API-Referenz

| Funktion | Parameter | Beschreibung |
|----------|-----------|--------------|
| `human_click(page, target)` | `target`: Selector oder Locator | Klickt mit Bézier-Mausbewegung + Delays |
| `human_type(page, target, text)` | `text`: Eingabetext | Tippt mit variabler Geschwindigkeit + Denkpausen |
| `human_scroll(page, target_y, duration)` | `duration`: Sekunden | Scrollt mit Beschleunigung/Verzögerung |
| `idle_time(page, duration)` | `duration`: Basis-Sekunden | Simuliert Lesezeit mit Mikro-Bewegungen |

---

## 🎭 Stealth Profile System

### Fingerprint-Konsistenz

Ein konsistentes Profil bedeutet:
- **User-Agent** ↔ **navigator.platform** ↔ **navigator.hardwareConcurrency**
- **Timezone** ↔ **IP-Geolocation** ↔ **locale**
- **WebGL Vendor/Renderer** ↔ **OS**

### Beispiel-Profil (Windows Chrome)

```python
{
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ... Chrome/124.0.0.0",
    "platform": "Win32",
    "vendor": "Google Inc.",
    "webgl_vendor": "Google Inc. (Intel)",
    "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 ...)",
    "languages": ["de-DE", "de", "en-US", "en"],
    "hw_concurrency": 8,
    "device_memory": 8,
    "timezone": "Europe/Berlin"
}
```

### Canvas & Audio Noise Injection

Wichtig: **Nicht blockieren!** Blockieren = sofortiges Bot-Flag.

Stattdessen wird subtiler Noise hinzugefügt:

```javascript
// Canvas: Minimale Farbvariation pro Session
const noiseSeed = 0.0023; // Zufällig, aber konsistent pro Session
img.data[i] += noiseSeed;

// AudioContext: Subtile Gain-Variation
d[i] += noiseSeed * Math.random();
```

### Timezone-Spoofing für Proxies

Wenn du Residential Proxies verwendest:

```python
from playstealth_actions.stealth_enhancer import apply_timezone_spoof

# IP-basierte Timezone ermitteln (z.B. via ipapi.co)
ip_tz = "America/New_York"

# Browser-Timezone spoofen
await apply_timezone_spoof(page, ip_tz)
```

---

## 🎯 Robuste Selektor-Heuristiken

### Die 8-fache Fallback-Hierarchie

`SmartClickAction` probiert nacheinander:

1. **aria-label**: `[aria-label="Weiter"]`
2. **data-testid**: `[data-testid="submit-btn"]`
3. **Button Text (exact)**: `button:has-text("Genau dieser Text")`
4. **Button Text (fuzzy)**: `button` enthält "Weiter" (60% Similarity)
5. **Link Text**: `a:has-text("Link Text")`
6. **Input Value/Placeholder**: `input[value="Submit"]` oder `[placeholder="Senden"]`
7. **role="button"**: `[role="button"]` mit Text-Match
8. **[onclick] Elements**: Fallback auf alte JS-Handler

### Beispiel

```python
from playstealth_actions.smart_actions import SmartClickAction

action = SmartClickAction()

# Sucht nach "Weiter" mit allen 8 Strategien
await action.execute(page, "Weiter")

# Erfolgsfall: Findet Button mit Text "Weiter zur nächsten Frage"
# Auch wenn:
# - Keine ID vorhanden
# - aria-label fehlt
# - data-testid dynamisch generiert wurde
```

### Fuzzy Matching Threshold

Standard: `0.6` (60% Similarität)

Anpassen bei False Positives:
```python
# In smart_actions.py, _find_by_fuzzy_text()
threshold = 0.75  # Strenger
```

---

## 💾 Session & State Management

### Vollständige Context-Persistenz

Beim Speichern einer Session wird gespeichert:
- ✅ CLI-State (aktueller Schritt, Umfrage-Index)
- ✅ Cookies (Login-Sessions, Tracking-Cookies)
- ✅ LocalStorage (Site-Präferenzen, Tokens)
- ✅ SessionStorage (temporäre Daten)
- ✅ IndexedDB (falls verwendet)
- ✅ Cache (Service Worker, Assets)

### Save/Resume Flow

```python
from playstealth_actions.state_store import (
    save_cli_state, 
    save_browser_state,
    load_cli_state,
    load_browser_context
)

# SPEICHERN
await save_browser_state(context, session_id="survey_123")
save_cli_state("survey_123", {
    "step": 5,
    "survey_index": 2,
    "last_action": "clicked_next"
})

# LADEN (nach Browser-Restart)
context = await load_browser_context(browser, session_id="survey_123")
page = await context.new_page()
state = load_cli_state("survey_123")
# Weitermachen bei step=5
```

### Session Cleanup

```python
from playstealth_actions.state_store import cleanup_session, list_sessions

# Alle Sessions auflisten
sessions = list_sessions()  # ["survey_123", "survey_456"]

# Session löschen
cleanup_session("survey_123")
```

---

## 🔍 Diagnostik & Leak-Tests

### Integrierte Checks

```bash
# Vollständiger Stealth-Check
playstealth diagnose benchmark

# Einzelne Checks
playstealth diagnose check-webgl
playstealth diagnose check-headless
playstealth diagnose check-timezone
```

### Score-Interpretation

| Score | Status | Empfehlung |
|-------|--------|------------|
| 100% | ✅ PASS | Produktionsreif |
| 80-99% | ⚠️ WARN | Review warnings vor Production |
| <80% | ❌ FAIL | Kritische Leaks beheben |

### Externe Validierung

Teste deine CLI gegen:
- **CreepJS**: https://abrahamjuliot.github.io/creepjs/
- **SannySoft**: https://bot.sannysoft.com/
- **Pixelscan**: https://pixelscan.net/

Erwartetes Ergebnis: **"Looks like a real browser"**

---

## ➕ Neue Survey-Typen hinzufügen

### Schritt 1: Plattform-spezifische Fallen identifizieren

Beispiel: **HeyPiggy Surveys**

```python
# Typische Fallen:
# 1. Consent-Banner mit dynamischer ID
# 2. Timer-basierte Fragen (mindestens 3s warten)
# 3. Honeypot-Felder (unsichtbare Inputs)
```

### Schritt 2: Plugin erstellen

```python
# plugins/heypiggy_plugin.py
from playstealth_actions.human_behavior import human_click, idle_time
from playstealth_actions.smart_actions import SmartClickAction

class HeyPiggyPlugin:
    async def handle_consent(self, page):
        # HeyPiggy verwendet kein Standard-Cookie-Banner
        # Stattdessen: Modal mit "privacy-notice-modal"
        modal = await page.query_selector("#privacy-notice-modal")
        if modal:
            await SmartClickAction().execute(page, "Akzeptieren")
    
    async def handle_question(self, page, question_data):
        # Mindestens 3s warten bei Timer-Fragen
        if question_data.get("has_timer"):
            await idle_time(page, duration=3.5)
        
        # Antwort auswählen
        await SmartClickAction().execute(page, question_data["answer"])
```

### Schritt 3: In Tool Registry integrieren

```python
# In tool_registry.py oder eigenem Entry Point
from plugins.heypiggy_plugin import HeyPiggyPlugin

plugin = HeyPiggyPlugin()
registry.register(
    name="heypiggy-consent",
    description="Handle HeyPiggy consent modal",
    category="platform",
    handler=plugin.handle_consent,
    parameters={}
)
```

---

## 🚀 Production Best Practices

### 1. Proxy-Konsistenz

```python
# Fingerprint MUSS zur IP passen
proxy_ip = "85.214.132.117"  # Germany
expected_tz = "Europe/Berlin"

profile = generate_user_agent()
profile["timezone"] = expected_tz
profile["locale"] = "de-DE"
```

### 2. Residential Proxies > Datacenter

| Proxy-Typ | Erkennungsrate | Kosten | Empfehlung |
|-----------|----------------|--------|------------|
| Datacenter | Hoch (80%+) | Niedrig | ❌ Testing only |
| Mobile 4G | Sehr niedrig | Hoch | ✅ Premium |
| Residential | Niedrig | Mittel | ✅ Production |

### 3. Rate Limiting

```python
# Max 3-5 Surveys pro Stunde pro IP
# Randomisiere Startzeiten: 12-18 Minuten zwischen Sessions
await asyncio.sleep(random.uniform(720, 1080))
```

### 4. Logging ohne Secrets

```python
# GUT
logger.info(f"Step {step}: Clicked 'Next' button")

# SCHLECHT (logged Credentials!)
logger.info(f"Typed password: {password}")
```

### 5. Self-Healing bei Fehlern

```python
from playstealth_actions.smart_actions import SmartClickAction
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def robust_click(page, target):
    try:
        return await SmartClickAction().execute(page, target)
    except Exception as e:
        logger.warning(f"Click failed: {e}, retrying...")
        raise
```

---

## 🧪 Test-Suite ausführen

```bash
# Alle Tests
pytest tests/ -v

# Einzelner Test
pytest tests/test_survey_flow.py::test_smart_click_with_button_text -v

# Mit Coverage
pytest tests/ --cov=playstealth_actions --cov-report=html
```

---

## ⚠️ Rechtliche Hinweise

1. **AGB-Compliance**: Automatisierung kann gegen Plattform-AGBs verstoßen
2. **Datenschutz**: Keine personenbezogenen Daten loggen
3. **Missbrauch**: Nicht für betrügerische Aktivitäten verwenden

**Nutze PlayStealth verantwortungsvoll.**

---

## 📞 Support & Contribution

- Issues: GitHub Issues
- Docs: `HACKING.md` (dieses Dokument)
- Tests: `pytest tests/ -v`

**Viel Erfolg beim Hacken!** 🎯
