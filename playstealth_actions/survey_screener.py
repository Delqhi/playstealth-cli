"""Survey Screener for disqualification detection and handling."""
import re
from playwright.async_api import Page

DISQUALIFY_PATTERNS = [
    r"(you do not qualify|disqualified|nicht geeignet|leider nicht|screened out|thank you for your interest)",
    r"(survey is full|umfrage voll|no longer available|bereits geschlossen)"
]

async def check_disqualification(page: Page) -> bool:
    """Check if page shows disqualification message."""
    content = await page.content()
    return any(re.search(pat, content, re.I) for pat in DISQUALIFY_PATTERNS)

async def handle_disqualification(page: Page, session_id: str, platform: str, dashboard_url: str):
    """Handle disqualification by returning to dashboard."""
    from .telemetry import log_event
    log_event(session_id, "disqualified", platform=platform)
    print("🚫 Disqualified → returning to dashboard")
    await page.goto(dashboard_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")
    return True
