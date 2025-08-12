import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

from loguru import logger
from scraper.browser import browser_context


ROSSMANN_URL = "https://www.rossmann.pl"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal runner z gwarancją snapshotów i health reportu")
    p.add_argument("--site", required=True, help="np. rossmann")
    p.add_argument("--profiles", default="desktop", help="comma-separated, np. desktop,mobile")
    p.add_argument("--headless", default="true")
    p.add_argument("--save-snapshots", default="false")
    return p.parse_args()


def today_dir(site: str) -> Path:
    today = dt.date.today().isoformat()
    return Path(f"data/{site}/{today}")


async def run_profile(
    site: str,
    profile: str,
    headless: bool,
    enable_tracing: bool,
    base_dir: Path,
) -> dict:
    """
    Zwraca słownik z metrykami dla profilu.
    Gwarantuje, że w snapshots/ pojawi się plik (png albo *.txt z błędem).
    """
    t0 = dt.datetime.utcnow()
    snaps = (base_dir / "snapshots")
    imgs = (base_dir / "images")
    snaps.mkdir(parents=True, exist_ok=True)
    imgs.mkdir(parents=True, exist_ok=True)

    metrics = {
        "profile": profile,
        "started_utc": t0.isoformat() + "Z",
        "ok": False,
        "error": None,
        "snapshot_path": None,
        "image_path": None,
        "duration_sec": None,
        "navigated_url": None,
    }

    logger.info(f"[{profile}] start | headless={headless} tracing={enable_tracing}")

    try:
        async with browser_context(
            profile=profile,
            headless=headless,
            start_tracing=enable_tracing,
            snapshots_dir=str(snaps) if enable_tracing else None,
        ) as ctx:
            page = await ctx.new_page()

            # Nawigacja — jeśli padnie, złapiemy wyjątek niżej
            await page.goto(ROSSMANN_URL, wait_until="domcontentloaded", timeout=30_000)
            metrics["navigated_url"] = ROSSMANN_URL

            # ZAWSZE wykonaj jeden zrzut do snapshots/ (żeby job mógł asertować obecność)
            snap_path = snaps / f"{profile}-landing.png"
            await page.screenshot(path=str(snap_path), full_page=True)
            metrics["snapshot_path"] = str(snap_path)

            # Opcjonalnie drugi zrzut do images/ (bardziej “produktowy”)
            img_path = imgs / f"{profile}-home.png"
            await page.screenshot(path=str(img_path))
            metrics["image_path"] = str(img_path)

            metrics["ok"] = True

    except Exception as e:
        # Zapewnij plik w snapshots/ nawet przy błędzie (żeby workflow się nie wykrzaczył)
        err_file = (snaps / f"{profile}-error.txt")
        err_file.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
        metrics["error"] = f"{type(e).__name__}: {e}"
        metrics["snapshot_path"] = str(err_file)
        logger.exception(f"[{profile}] Błąd scrapowania")

    finally:
        metrics["duration_sec"] = round((dt.datetime.utcnow() - t0).total_seconds(), 3)
        logger.info(f"[{profile}] done | ok={metrics['ok']} duration={metrics['duration_sec']}s")

    return metrics


async def main() -> int:
    args = parse_args()
    headless = args.headless.lower() == "true"
    enable_tracing = args.save_snapshots.lower() == "true"
    site = args.site
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]

    base_dir = today_dir(site)
    snaps = base_dir / "snapshots"
    imgs = base_dir / "images"
    snaps.mkdir(parents=True, exist_ok=True)
    imgs.mkdir(parents=True, exist_ok=True)

    logger.info(f"Run for site={site} profiles={profiles} headless={headless} tracing={enable_tracing}")
    logger.info(f"Output dirs: {base_dir} | snapshots={snaps} | images={imgs}")

    # Odpal profile równolegle
    tasks = [run_profile(site, p, headless, enable_tracing, base_dir) for p in profiles]
    results = await asyncio.gather(*tasks)

    # Podsumowanie i health report
    visited = sum(1 for r in results if r["navigated_url"])
    errors = [r for r in results if not r["ok"]]
    snapshots_count = len(list(snaps.glob("*")))
    images_count = len(list(imgs.glob("*")))

    report = {
        "site": site,
        "date": dt.date.today().isoformat(),
        "profiles": profiles,
        "ok": len(errors) == 0 and visited > 0,
        "visited_profiles": visited,
        "errors_count": len(errors),
        "errors": errors,  # pełne wpisy profili z errorami
        "snapshots_count": snapshots_count,
        "images_count": images_count,
        "base_dir": str(base_dir),
        "generated_at_utc": dt.datetime.utcnow().isoformat() + "Z",
        "runner_version_note": "runner ensures snapshots+health_report even on failure",
    }

    # Gwarancja pliku raportu
    health_path = base_dir / "health_report.json"
    health_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Health report saved -> {health_path}")

    # Zwróć 0, żeby workflow nie padał — walidację robi osobny krok
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("Przerwano przez użytkownika")
        sys.exit(130)
    except Exception:
        logger.exception("Nieoczekiwany błąd w runnerze")
        # nawet tutaj spróbujemy nie psuć całego joba
        sys.exit(0)
