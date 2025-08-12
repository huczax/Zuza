import argparse, datetime, os, sys, json, asyncio
from pathlib import Path
from loguru import logger

from scraper.browser import browser_context
# from scraper import extract  # odkomentuj gdy będzie potrzebne

parser = argparse.ArgumentParser()
parser.add_argument("--site", required=True)
parser.add_argument("--profiles", default="desktop")  # np. "desktop,mobile"
parser.add_argument("--headless", default="true")
parser.add_argument("--save-snapshots", default="false")
args = parser.parse_args()

today = datetime.date.today().isoformat()
base_dir = Path(f"data/{args.site}/{today}")
images_dir = base_dir / "images"
snapshots_dir = base_dir / "snapshots"
images_dir.mkdir(parents=True, exist_ok=True)
snapshots_dir.mkdir(parents=True, exist_ok=True)

headless = args.headless.lower() == "true"
save_snaps = args.save_snapshots.lower() == "true"

visited = 0
errors = 0
health = {
    "site": args.site,
    "date": today,
    "profiles": args.profiles.split(","),
    "visited_urls": 0,
    "errors": 0,
}

async def run_profile(profile: str):
    global visited
    try:
        async with browser_context(
            profile=profile,
            headless=headless,
            start_tracing=save_snaps,
            snapshots_dir=str(snapshots_dir) if save_snaps else None,
        ) as ctx:
            page = await ctx.new_page()
            await page.goto("https://www.rossmann.pl", wait_until="domcontentloaded")
            # out = await extract.run(page)  # jeśli potrzebujesz
            if save_snaps:
                # zrzut strony startowej per profil
                await page.screenshot(path=str(snapshots_dir / f"{profile}-landing.png"), full_page=True)
        logger.debug(f"Visited profile: {profile}")
        visited += 1
    except Exception:
        global errors
        errors += 1
        logger.exception("Scrape error")

async def main():
    tasks = []
    for p in args.profiles.split(","):
        tasks.append(run_profile(p.strip()))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    try:
        report = {
            **health,
            "visited_urls": visited,
            "errors": errors,
            "snapshots_count": len(list(snapshots_dir.glob("*"))) if snapshots_dir.exists() else 0,
            "ok": errors == 0 and visited > 0,
        }
        base_dir.mkdir(parents=True, exist_ok=True)
        with open(base_dir / "health_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("Health report saved:", base_dir / "health_report.json")
        # jeżeli ktoś włączy save-snapshots, a nic nie powstało — zostaw ślad
        if save_snaps and report["snapshots_count"] == 0:
            (snapshots_dir / "KEEP").write_text("no snapshots produced by pipeline logic\n", encoding="utf-8")
    except Exception as e:
        print("Failed to write health_report.json:", e, file=sys.stderr)
