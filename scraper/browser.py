# scraper/browser.py
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

# Uwaga: Playwright ładowany leniwie wewnątrz kontekstu,
# żeby import tego modułu nie wymagał zainstalowanego playwrighta.
# from playwright.async_api import async_playwright

# Presety profili: "desktop" i "mobile".
# W razie potrzeby dodaj kolejne wpisy.
PROFILE_PRESETS: Dict[str, Dict[str, Any]] = {
    "desktop": {
        "viewport": {"width": 1366, "height": 768},
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    "mobile": {
        "viewport": {"width": 390, "height": 844},  # iPhone 15-ish
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    },
}


def _context_kwargs_for_profile(profile: str) -> Dict[str, Any]:
    """
    Zwraca kwargs do browser.new_context() dla wybranego profilu.
    """
    preset = PROFILE_PRESETS.get(profile.lower())
    if not preset:
        # fallback na desktop, jeżeli ktoś poda literówkę
        preset = PROFILE_PRESETS["desktop"]
    # Skopiuj, żeby modyfikacje nie dotykały oryginału
    return dict(preset)


@asynccontextmanager
async def browser_context(
    profile: str = "desktop",
    headless: bool = True,
    start_tracing: bool = False,
    snapshots_dir: Optional[str] = None,
    extra_context_kwargs: Optional[Dict[str, Any]] = None,
):
    """
    Kontekst Playwright:
      - uruchamia Chromium w trybie headless (domyślnie),
      - tworzy context zgodny z profilem ("desktop" | "mobile"),
      - opcjonalnie uruchamia tracing (screenshots + snapshots),
      - po wyjściu zapisuje trace.zip do snapshots_dir (gdy włączony tracing).

    Przykład:
        async with browser_context("desktop", headless=True, start_tracing=True,
                                   snapshots_dir="data/rossmann/2025-01-01/snapshots") as ctx:
            page = await ctx.new_page()
            await page.goto("https://example.com")
    """
    from playwright.async_api import async_playwright  # lokalny import

    async with async_playwright() as pw:
        # Kilka bezpiecznych flag pod CI (ogranicza problemy z pamięcią współdzieloną)
        launch_args = ["--disable-dev-shm-usage"]
        browser = await pw.chromium.launch(headless=headless, args=launch_args)

        ctx_kwargs = _context_kwargs_for_profile(profile)
        if extra_context_kwargs:
            ctx_kwargs.update(extra_context_kwargs)

        context = await browser.new_context(**ctx_kwargs)

        try:
            if start_tracing:
                await context.tracing.start(screenshots=True, snapshots=True)
            yield context
        finally:
            # Zakończ tracing i zapisz paczkę, jeśli proszono
            if start_tracing:
                if snapshots_dir:
                    out_dir = Path(snapshots_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    await context.tracing.stop(path=str(out_dir / "trace.zip"))
                else:
                    # Zatrzymaj bez zapisu do pliku (na wszelki wypadek)
                    await context.tracing.stop()
            await context.close()
            await browser.close()
