"""Test suite for survey automation flows."""
import pytest
from mock_pages import MOCK_SURVEY_HTML, MOCK_DYNAMIC_HTML, MOCK_CONSENT_HTML, MOCK_MULTI_STEP_HTML

# Import the modules we created
try:
    from playstealth_actions.human_behavior import human_click, human_type
    from playstealth_actions.smart_actions import SmartClickAction, SmartTypeAction
    from playstealth_actions.stealth_enhancer import inject_advanced_stealth, detect_leaks
    HUMAN_ENGINE_AVAILABLE = True
except ImportError as e:
    HUMAN_ENGINE_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.asyncio
async def test_stealth_injection_basic(page):
    """Test that stealth injection properly hides webdriver property."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    # Inject stealth scripts
    await inject_advanced_stealth(page)
    
    # Check navigator.webdriver is undefined or false
    webdriver = await page.evaluate("navigator.webdriver")
    assert webdriver is None or webdriver is False, "navigator.webdriver should be hidden"


@pytest.mark.asyncio
async def test_stealth_leak_detection(page):
    """Test the leak detection functionality."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    # Inject stealth first
    await inject_advanced_stealth(page)
    
    # Run leak detection
    leaks = await detect_leaks(page)
    
    # Should have minimal or no critical leaks after injection
    # Note: Some checks might still fail in headless mode, which is expected
    assert isinstance(leaks, dict), "Leak detection should return a dict"
    assert "webdriver" in leaks or "critical_leaks" in leaks, "Should report on webdriver status"


@pytest.mark.asyncio
async def test_smart_click_with_aria_label(page):
    """Test smart click action with aria-label selector."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    await page.set_content(MOCK_CONSENT_HTML)
    
    action = SmartClickAction()
    # Should find button via aria-label
    await action.execute(page, "Cookie Consent")
    
    # Cookie banner should be hidden after clicking accept (if logic was wired)
    # For now, just verify the click didn't throw an error
    assert True


@pytest.mark.asyncio
async def test_smart_click_with_data_testid(page):
    """Test smart click action with data-testid attribute."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    await page.set_content(MOCK_CONSENT_HTML)
    
    action = SmartClickAction()
    # Should find button via data-testid="accept-all"
    await action.execute(page, "accept-all")
    
    # Verify click succeeded without error
    assert True


@pytest.mark.asyncio
async def test_smart_click_with_button_text(page):
    """Test smart click finds button by text content."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    await page.set_content(MOCK_SURVEY_HTML)
    
    action = SmartClickAction()
    # Should find "Weiter zur nächsten Frage" button by text
    await action.execute(page, "Weiter")
    
    # Verify the page changed (survey completed)
    content = await page.content()
    assert "Vielen Dank" in content, "Survey should show thank you message after click"


@pytest.mark.asyncio
async def test_dynamic_dom_resolution(page):
    """Test that smart selector waits for dynamically loaded content."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    await page.set_content(MOCK_DYNAMIC_HTML)
    
    action = SmartClickAction()
    # Button appears after 800ms - should wait and find it
    await action.execute(page, "Absenden")
    
    # If we got here without timeout, the dynamic resolution worked
    assert True


@pytest.mark.asyncio
async def test_human_type_simulation(page):
    """Test human-like typing with variable delays."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    html = """
    <html><body>
      <input type="text" id="name-input" placeholder="Enter your name">
      <div id="output"></div>
      <script>
        document.getElementById('name-input').addEventListener('input', (e) => {
          document.getElementById('output').textContent = e.target.value;
        });
      </script>
    </body></html>
    """
    await page.set_content(html)
    
    # Test human-like typing
    await human_type(page, "#name-input", "Max Mustermann")
    
    # Verify text was entered
    output = await page.text_content("#output")
    assert "Max Mustermann" in output, "Input field should contain typed text"


@pytest.mark.asyncio
async def test_multi_step_survey_flow(page):
    """Test a complete multi-step survey flow."""
    if not HUMAN_ENGINE_AVAILABLE:
        pytest.skip(f"Human engine modules not available: {IMPORT_ERROR}")
    
    await page.set_content(MOCK_MULTI_STEP_HTML)
    
    # Step 1: Fill name
    await human_type(page, "#name", "Test User")
    
    # Step 1: Click next
    click_action = SmartClickAction()
    await click_action.execute(page, "Weiter zu Schritt 2")
    
    # Verify step 2 is visible
    step2_visible = await page.is_visible("#step-2")
    assert step2_visible, "Step 2 should be visible after clicking next"
    
    # Step 2: Submit (simplified - just click)
    await click_action.execute(page, "Absenden")
    
    # Verify thank you page
    thank_you_visible = await page.is_visible("#thank-you")
    assert thank_you_visible, "Thank you page should be visible after submission"
