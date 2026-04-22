import pytest
import asyncio
from playwright.async_api import async_playwright

pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()

@pytest.fixture
async def browser():
    """Create a Chromium browser instance for testing."""
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        yield b
        await b.close()

@pytest.fixture
async def context(browser):
    """Create a browser context with standard viewport."""
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    yield ctx
    await ctx.close()

@pytest.fixture
async def page(context):
    """Create a new page in the context."""
    p = await context.new_page()
    yield p
    await p.close()
