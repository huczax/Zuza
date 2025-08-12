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

@asynccontextmanager
async def browser_context(profile: str = "desktop", headless: bool = True):
    proxy = os.getenv("PROXY_URL") or None
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=headless, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox","--disable-dev-shm-usage",
        ])
        viewport = random.choice(DESKTOP_VIEWPORTS if profile=="desktop" else MOBILE_VIEWPORTS)
        ua = _pick_ua(profile)
        context = await b.new_context(
            user_agent=ua,
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=1.0 if profile=="desktop" else 2.0,
            is_mobile=(profile!="desktop"),
            proxy={"server": proxy} if proxy else None,
            java_script_enabled=True,
            locale="pl-PL",
        )
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        try:
            yield context
        finally:
            await context.close()
            await b.close()
