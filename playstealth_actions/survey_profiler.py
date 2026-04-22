"""Survey Profiler: Analysiert DOM-Struktur, Fragetypen, Navigation, Consent und Fallen."""
import re
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page
from typing import Dict, Any, List, Optional

# Relative imports für modulare Architektur
try:
    from .trap_detector import detect_honeypots, parse_attention_check
except ImportError:
    # Fallback für direkte Ausführung oder Tests
    import sys
    sys.path.append(str(Path(__file__).parent))
    from trap_detector import detect_honeypots, parse_attention_check

# Lokale Profile-Definition (minimal für Profiling)
def generate_profile(key: str = "win_chrome"):
    """Generiert ein einfaches Browser-Profil für Profiling."""
    profiles = {
        "win_chrome": {
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "Win32",
            "languages": ["de-DE", "de", "en-US", "en"],
            "timezone": "Europe/Berlin"
        },
        "mac_chrome": {
            "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "MacIntel",
            "languages": ["de-DE", "de", "en-US", "en"],
            "timezone": "Europe/Berlin"
        }
    }
    return profiles.get(key, profiles["win_chrome"])

async def apply_stealth_profile(ctx, profile: dict):
    """Wendet Stealth-Injections auf den Browser-Kontext an."""
    from .stealth_enhancer import inject_advanced_stealth
    try:
        page = await ctx.new_page()
        await inject_advanced_stealth(page)
        await page.close()
    except Exception:
        pass  # Optional, nicht kritisch für Profiling

PLUGIN_DIR = Path(__file__).parent / "plugins"
TEST_DIR = Path(__file__).parent.parent / "tests"

async def _extract_dom_metrics(page: Page) -> Dict[str, Any]:
    """Extrahiert survey-relevante DOM-Muster sicher & performant."""
    js = """
    () => {
        const safeText = (el) => (el.innerText || el.value || '').trim().slice(0, 250);
        const safeClasses = (el) => (el.className || '').split(' ').filter(c => c.length > 1 && c.length < 30).slice(0, 3);
        
        const metrics = { questions: [], options: [], navigation: [], consent: [], forms: [] };
        
        // Questions
        document.querySelectorAll('h1, h2, h3, .question, [class*="question"], [class*="q-"], [class*="prompt"], label').forEach(el => {
            const txt = safeText(el);
            if (txt.length > 8 && txt.length < 400) {
                metrics.questions.push({ 
                    text: txt, 
                    tag: el.tagName, 
                    classes: safeClasses(el), 
                    id: el.id || null 
                });
            }
        });
        
        // Options
        document.querySelectorAll('input[type="radio"], input[type="checkbox"], select, textarea, [role="radio"], [role="checkbox"], .option, [class*="choice"]').forEach(el => {
            metrics.options.push({
                type: el.type || el.tagName.toLowerCase(),
                name: el.name || null,
                id: el.id || null,
                classes: safeClasses(el),
                text: safeText(el.parentElement) || safeText(el)
            });
        });
        
        // Navigation
        const navRe = /next|weiter|submit|continue|absenden|fortfahren|save|speichern|weiter zur/i;
        document.querySelectorAll('button, a, [role="button"], input[type="submit"]').forEach(el => {
            const txt = safeText(el);
            if (navRe.test(txt)) {
                metrics.navigation.push({ 
                    text: txt, 
                    tag: el.tagName, 
                    id: el.id || null, 
                    classes: safeClasses(el) 
                });
            }
        });
        
        // Consent
        const consentRe = /accept|akzeptieren|agree|zustimmen|cookie|consent|datenschutz|alle akzeptieren/i;
        document.querySelectorAll('button, a, [role="button"]').forEach(el => {
            const txt = safeText(el);
            if (consentRe.test(txt)) {
                metrics.consent.push({ 
                    text: txt, 
                    id: el.id || null, 
                    classes: safeClasses(el) 
                });
            }
        });
        
        // Forms
        document.querySelectorAll('form').forEach(f => {
            metrics.forms.push({ 
                id: f.id || null, 
                action: f.action || null, 
                method: f.method || null, 
                fields: f.querySelectorAll('input, select, textarea').length 
            });
        });
        
        return metrics;
    }
    """
    try:
        return await page.evaluate(js)
    except Exception as e:
        return {
            "error": f"DOM extraction failed: {e}", 
            "questions": [], 
            "options": [], 
            "navigation": [], 
            "consent": [], 
            "forms": []
        }

def _generate_plugin_stub(name: str, report: Dict[str, Any]) -> str:
    """Erzeugt Plugin-Code basierend auf Profiler-Ergebnissen."""
    if not re.match(r'^[a-z0-9_]+$', name):
        raise ValueError("Plugin name must be lowercase alphanumeric + underscores only.")
    
    class_name = "".join(part.capitalize() for part in name.split("_")) + "Platform"
    
    # Extrahiere beste Navigation/Consent Optionen
    nav_items = report["dom_structure"].get("navigation", [])
    consent_items = report["dom_structure"].get("consent", [])
    
    nav = nav_items[0] if nav_items else {"text": "Next", "id": None}
    consent = consent_items[0] if consent_items else {"text": "Accept", "id": None}
    
    # Baue Locator-Strings
    nav_loc = f"#{nav['id']}" if nav.get('id') else f"'{nav['text']}'"
    consent_loc = f"#{consent['id']}" if consent.get('id') else f"'{consent['text']}'"
    
    # Generische Selektoren basierend auf gefundenen Mustern
    q_sel = ".question, h2, [class*='question'], [class*='q-']"
    opt_sel = "input[type='radio'], input[type='checkbox'], select, [role='radio'], [role='checkbox']"
    
    domain = re.sub(r'^https?://', '', report["url"]).split('/')[0]
    
    return f'''"""Auto-profiled plugin for {report["url"]}
Generated by playstealth profile. Review & adjust selectors before production use."""
import re
from playwright.async_api import Page
from .base_platform import BasePlatform
from ..human_engine import human_click
from ..smart_selector import resolve_locator
from ..trap_detector import analyze_page_traps

class {class_name}(BasePlatform):
    """Survey platform plugin generated from DOM profiling."""

    async def detect(self, page: Page) -> bool:
        url = page.url.lower()
        return "{domain}" in url

    async def handle_consent(self, page: Page) -> bool:
        try:
            btn = await resolve_locator(page, {consent_loc})
            if await btn.is_visible(timeout=3000):
                await human_click(page, btn)
                return True
        except Exception:
            pass
        return False

    async def get_current_step(self, page: Page):
        q_loc = page.locator("{q_sel}").first
        try:
            q_text = await q_loc.inner_text(timeout=5000)
        except Exception:
            q_text = "Unknown question"
        
        opts = await page.locator("{opt_sel}").all()
        return {{"question": q_text.strip(), "option_count": len(opts), "type": "{name}_choice"}}

    async def answer_question(self, page: Page, answer_data) -> bool:
        q_data = await self.get_current_step(page)
        opts_els = await page.locator("{opt_sel}").all()
        
        # Hole Text für Trap-Detection
        opts_text = []
        for o in opts_els:
            try:
                parent = await o.element_handle()
                txt = await parent.inner_text() if parent else ""
                opts_text.append(txt)
            except:
                opts_text.append("")
        
        # 🛡️ Trap-Override
        trap = await analyze_page_traps(page, q_data["question"], opts_text)
        if trap and trap.get("attention_check") and trap["attention_check"].get("action") == "select_index":
            answer_data = trap["attention_check"]["index"]

        if isinstance(answer_data, int) and 0 <= answer_data < len(opts_els):
            await human_click(page, opts_els[answer_data])
            return True
        return False

    async def navigate_next(self, page: Page) -> bool:
        try:
            await human_click(page, {nav_loc})
            return True
        except Exception:
            return False

    async def is_completed(self, page: Page) -> bool:
        try:
            content = await page.content()
            return bool(re.search(r"(thank you|completed|danke|abgeschlossen|response.*recorded|vielen dank)", content, re.I))
        except:
            return False
'''

async def profile_survey(url: str, output_name: Optional[str] = None) -> Dict[str, Any]:
    """Profiliert Survey-URL, analysiert Struktur/Fallen & generiert Plugin-Stub."""
    if not output_name:
        domain = re.sub(r'^https?://', '', url).split('/')[0].replace('.', '_').replace('-', '_')
        output_name = f"profiled_{domain}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        profile = generate_profile("win_chrome")
        ctx = await browser.new_context(
            user_agent=profile["ua"],
            locale=profile["languages"][0],
            timezone_id=profile["timezone"],
            viewport={"width": 1920, "height": 1080}
        )
        await apply_stealth_profile(ctx, profile)
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            await browser.close()
            return {"error": f"Navigation failed: {e}", "url": url}

        dom = await _extract_dom_metrics(page)
        honeypots = await detect_honeypots(page)

        # Frage-Typen klassifizieren
        q_types = {"radio": 0, "checkbox": 0, "text": 0, "select": 0, "other": 0}
        for opt in dom.get("options", []):
            t = opt.get("type", "").lower()
            if "radio" in t: q_types["radio"] += 1
            elif "checkbox" in t: q_types["checkbox"] += 1
            elif "text" in t or "textarea" in t: q_types["text"] += 1
            elif "select" in t: q_types["select"] += 1
            else: q_types["other"] += 1

        # Attention-Check Vorschau (erste Frage)
        first_q = dom["questions"][0]["text"] if dom["questions"] else ""
        first_opts = [o.get("text", "") for o in dom["options"][:5]]
        attention_preview = parse_attention_check(first_q, first_opts)

        report = {
            "url": url,
            "generated_plugin": output_name,
            "dom_structure": dom,
            "question_types": q_types,
            "honeypots_detected": len(honeypots),
            "honeypots": honeypots,
            "attention_check_preview": attention_preview,
            "navigation_buttons": len(dom.get("navigation", [])),
            "consent_buttons": len(dom.get("consent", [])),
            "forms_found": len(dom.get("forms", []))
        }

        # Plugin & Test generieren
        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        TEST_DIR.mkdir(parents=True, exist_ok=True)
        plugin_path = PLUGIN_DIR / f"{output_name}.py"
        test_path = TEST_DIR / f"test_plugin_{output_name}.py"

        if plugin_path.exists():
            report["warning"] = f"Plugin already exists: {plugin_path}. Skipped generation."
        else:
            with open(plugin_path, "w", encoding="utf-8") as f:
                f.write(_generate_plugin_stub(output_name, report))
            
            class_name = "".join(p.capitalize() for p in output_name.split("_")) + "Platform"
            test_content = f'''"""Tests for {output_name} plugin."""
import pytest
from playwright.async_api import Page
from playstealth_actions.plugins.{output_name} import {class_name}

@pytest.mark.asyncio
async def test_detect_{output_name}(page: Page):
    plugin = {class_name}()
    # TODO: Mock URL/DOM for detection
    assert await plugin.detect(page) is False

@pytest.mark.asyncio
async def test_handle_consent_{output_name}(page: Page):
    plugin = {class_name}()
    # TODO: Implement consent test
    pass
'''
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_content)
            
            report["plugin_path"] = str(plugin_path)
            report["test_path"] = str(test_path)

        await browser.close()
        return report
