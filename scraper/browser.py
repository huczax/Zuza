from contextlib import asynccontextmanager
from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import async_playwright
import os, random, yaml, pathlib

load_dotenv()

DESKTOP_VIEWPORTS = [(1280,800),(1440,900),(1600,900),(1920,1080)]
MOBILE_VIEWPORTS  = [(390,844),(412,915),(360,780),(393,873)]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
"""

def _pick_ua(profile: str) -> str | None:
    st = yaml.safe_load(pathlib.Path("config/settings.yaml").read_text())
    pool = st.get("user_agents", {}).get("desktop" if profile=="desktop" else "mobile", [])
    return random.choice(pool) if pool else None

from contextlib import asynccontextmanager
from pathlib import Path

@asynccontextmanager
async def browser_context(
    profile: str = "desktop",
    headless: bool = True,
    start_tracing: bool = False,
    snapshots_dir: str | None = None,
):
    """
    Tworzy kontekst przeglądarki Playwright z ustawieniami profilu.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768} if profile == "desktop" else {"width": 390, "height": 844}
        )
        try:
            if start_tracing:
                await ctx.tracing.start(screenshots=True, snapshots=True)
            yield ctx
        finally:
            if start_tracing and snapshots_dir:
                Path(snapshots_dir).mkdir(parents=True, exist_ok=True)
                await ctx.tracing.stop(path=str(Path(snapshots_dir) / "trace.zip"))
            await ctx.close()
            await browser.close()
