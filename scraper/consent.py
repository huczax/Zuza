from contextlib import asynccontextmanager
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright

@asynccontextmanager
async def browser_context(
    profile: str = "desktop",
    headless: bool = True,
    start_tracing: bool = False,
    snapshots_dir: str | None = None,  # zachowane dla zgodności
    trace_dir: str | None = None,      # NOWE: gdzie zapisać trace .zip
    consent: str = "auto",             # przyszłościowo; runner steruje consentem
):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)

    ctx = await browser.new_context(
        viewport={"width": 1366, "height": 900} if profile == "desktop" else {"width": 390, "height": 844},
        device_scale_factor=1,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            if profile != "desktop"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
        ),
    )

    if start_tracing:
        try:
            await ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
            logger.debug("[trace] start")
        except Exception as e:
            logger.warning(f"[trace] start failed: {e}")

    try:
        yield ctx
    finally:
        if start_tracing:
            try:
                out = (Path(trace_dir) if trace_dir else Path("traces"))
                out.parent.mkdir(parents=True, exist_ok=True)
                # jeżeli podano katalog, zapiszemy jako traces.zip w tym katalogu
                path = out if out.suffix == ".zip" else out.with_suffix(".zip")
                await ctx.tracing.stop(path=str(path))
                logger.debug(f"[trace] saved -> {path}")
            except Exception as e:
                logger.warning(f"[trace] stop failed: {e}")
        await ctx.close()
        await browser.close()
        await pw.stop()
