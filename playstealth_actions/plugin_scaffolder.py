"""Plugin-Template-Generator für PlayStealth CLI.

Erzeugt Boilerplate + pytest-Async-Tests für neue Survey-Plattformen.
Validiert Namen, verhindert Überschreiben, gibt klare Next-Steps.
"""
import re
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent / "plugins"
TEST_DIR = Path(__file__).parent.parent / "tests"

PLUGIN_TEMPLATE = '''"""Auto-generated plugin for {name} survey platform."""
import re
from playwright.async_api import Page
from .base_platform import BasePlatform
from ..human_behavior import human_click
from ..smart_actions import SmartClickAction
from ..trap_detector import analyze_page_traps


class {class_name}(BasePlatform):
    """Plugin for {name} surveys."""

    async def detect(self, page: Page) -> bool:
        # TODO: URL/DOM detection logic
        url = page.url.lower()
        return "{name}" in url

    async def handle_consent(self, page: Page) -> bool:
        try:
            btn = await SmartClickAction().execute(page, "Accept")
            if await btn.is_visible(timeout=2000):
                await human_click(page, btn)
                return True
        except Exception:
            pass
        return False

    async def get_current_step(self, page: Page):
        # TODO: Extract question text & options
        q_text = "Unknown question"
        opts = []
        return {{"question": q_text, "option_count": len(opts), "type": "{name}_choice"}}

    async def answer_question(self, page: Page, answer_data) -> bool:
        q_data = await self.get_current_step(page)
        
        # TODO: Trap detection & answer logic
        # opts_text = [await o.inner_text() for o in await page.locator("input, button").all()]
        # trap = await analyze_page_traps(page, q_data["question"], opts_text)
        
        if isinstance(answer_data, int):
            opts = await page.locator("input[type='radio'], input[type='checkbox'], button, [role='radio']").all()
            if 0 <= answer_data < len(opts):
                await human_click(page, opts[answer_data])
                return True
        return False

    async def navigate_next(self, page: Page) -> bool:
        try:
            await SmartClickAction().execute(page, "Next")
            return True
        except Exception:
            return False

    async def is_completed(self, page: Page) -> bool:
        content = await page.content()
        return bool(re.search(r"(thank you|completed|danke|abgeschlossen)", content, re.I))
'''

TEST_TEMPLATE = '''"""Tests for {name} plugin."""
import pytest
from playwright.async_api import Page
from playstealth_actions.plugins.{module_name} import {class_name}


@pytest.mark.asyncio
async def test_detect_{name}(page: Page):
    plugin = {class_name}()
    await page.set_content("<html><body>test</body></html>")
    # TODO: Mock URL/DOM for detection
    assert await plugin.detect(page) is False


@pytest.mark.asyncio
async def test_handle_consent_{name}(page: Page):
    plugin = {class_name}()
    await page.set_content('<button>Accept</button>')
    # TODO: Implement consent test
    # result = await plugin.handle_consent(page)
    # assert result is True


@pytest.mark.asyncio
async def test_answer_question_{name}(page: Page):
    plugin = {class_name}()
    html_content = """
        <html><body>
            <h2>Question?</h2>
            <input type="radio" name="q1" value="a"> Option A
            <input type="radio" name="q1" value="b"> Option B
        </body></html>
    """
    await page.set_content(html_content)
    # TODO: Implement answer test
    # result = await plugin.answer_question(page, 0)
    # assert result is True
'''


def create_plugin(name: str) -> dict:
    """
    Erstellt ein neues Plugin mit Boilerplate-Code und Tests.
    
    Args:
        name: Plugin-Name (lowercase, alphanumeric + underscores)
        
    Returns:
        Dictionary mit erstellten Pfaden und Next-Steps
        
    Raises:
        ValueError: Bei ungültigem Plugin-Namen
        FileExistsError: Wenn Plugin bereits existiert
    """
    if not re.match(r'^[a-z0-9_]+$', name):
        raise ValueError("Plugin name must be lowercase alphanumeric + underscores only (e.g., survey_monkey).")

    class_name = "".join(part.capitalize() for part in name.split("_")) + "Platform"
    module_name = name

    plugin_path = PLUGIN_DIR / f"{module_name}.py"
    test_path = TEST_DIR / f"test_plugin_{module_name}.py"

    if plugin_path.exists():
        raise FileExistsError(f"Plugin already exists: {plugin_path}")

    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    with open(plugin_path, "w", encoding="utf-8") as f:
        f.write(PLUGIN_TEMPLATE.format(name=name, class_name=class_name))

    with open(test_path, "w", encoding="utf-8") as f:
        f.write(TEST_TEMPLATE.format(name=name, class_name=class_name, module_name=module_name))

    return {
        "status": "created",
        "plugin_path": str(plugin_path),
        "test_path": str(test_path),
        "class_name": class_name,
        "next_steps": [
            f"Edit {plugin_path} and implement detect()/answer_question()",
            f"Add tests to {test_path}",
            "Run: pytest tests/ -v"
        ]
    }
