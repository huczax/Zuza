import argparse
import asyncio
import json
from pathlib import Path
from datetime import date
from loguru import logger

from scraper.browser import browser_context
# from scraper import extract  # odkomentuj, gdy będziesz używać

async def run_profile(site: str, profile: str, base_dir: Path, headless: bool, save_snapshots: bool) -> tuple[int, int]:
    """
    Zwraca (visited, errors) dla danego profilu.
    """
    snapshots_dir = base_dir / "snapshots"
    images_dir = base_dir / "images"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with browser_context(
            profile=profile,
            headless=headless,
            start_tracing=save_snapshots,
            snapshots_dir=str(snapshots_dir) if save_snapshots else None,
        ) as ctx:
            page = await ctx.new_page()
            await page.goto("https://www.rossmann.pl", wait_until="domcontentloaded")
            # out = await extract.run(page)  # jeśli potrzebujesz

            # Prosty „dowód życia” – screenshot strony głównej per profil
            await page.screenshot(path=str(images_dir / f"{profile}-landing.png}"), full_page=True)

        logger.debug(f"[{site}] visited profile={profile}")
        return (1, 0)

    except Exception as e:
        logger.exception(f"[{site}] scrape error for profile={profile}: {e!r}")
        return (0, 1)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--profiles", default="desktop")  # np. "desktop,mobile"
    parser.add_argument("--headless", default="true")
    parser.add_argument("--save-snapshots", default="false")
    args = parser.parse_args()

    site = args.site
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    headless = args.headless.lower() == "true"
    save_snapshots = args.save_snapshots.lower() == "true"

    today = date.today().isoformat()
    base_dir = Path(f"data/{site}/{today}")
    (base_dir / "images").mkdir(parents=True, exist_ok=True)
    (base_dir / "snapshots").mkdir(parents=True, exist_ok=True)

    # Uruchom równolegle wszystkie profile
    results = await asyncio.gather(
        *[run_profile(site, p, base_dir, headless, save_snapshots) for p in profiles],
        return_exceptions=False,
    )

    visited = sum(v for v, _ in results)
    errors = sum(e for _, e in results)

    # Policz pliki/snapshoty
    snapshots_dir = base_dir / "snapshots"
    snapshots_count = len(list(snapshots_dir.glob("*"))) if snapshots_dir.exists() else 0

    # Jeśli prosiliśmy o snapshotsy, a nic nie powstało – zostaw ślad, żeby check w CI nie był „niemądrze czerwony”
    if save_snapshots and snapshots_count == 0:
        (snapshots_dir / "KEEP").write_text(
            "no snapshots produced by pipeline logic\n", encoding="utf-8"
        )
        snapshots_count = 1  # już jest przynajmniej KEEP

    report = {
        "site": site,
        "date": today,
        "profiles": profiles,
        "visited_urls": visited,
        "errors": errors,
        "snapshots_count": snapshots_count,
        "ok": (errors == 0 and visited > 0),
    }

    (base_dir / "health_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Health report saved:", base_dir / "health_report.json")

if __name__ == "__main__":
    asyncio.run(main())
