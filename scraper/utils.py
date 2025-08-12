from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import re

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=5))
async def safe_goto(page, url: str, timeout_ms: int = 30000):
    logger.debug(f"goto: {url}")
    await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

async def network_settle(page, idle_ms: int = 1500):
    await page.wait_for_timeout(idle_ms)

def pick_best_from_srcset(srcset: str) -> str | None:
    if not srcset: return None
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    return parts[-1].split()[0] if parts else None
