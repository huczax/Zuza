import argparse, yaml, pathlib, json, asyncio
from loguru import logger
from .browser import browser_context
from .utils import safe_goto, network_settle
from .extract import extract_section
from .storage import TODAY_DIR, JsonlWriter, save_snapshot
from .health import validate
from .diffing import compute_diff
from .alerts import send_email

DEF_HEADLESS=True

async def run(site_key: str, profiles: list[str], headless: bool, save_snaps: bool):
    site_cfg = yaml.safe_load(pathlib.Path(f"config/sites/{site_key}.yaml").read_text())
    sections = site_cfg.get("sections", [])
    base_url = site_cfg["site"]["entry_url"]

    all_results = []
    for profile in profiles:
        async with browser_context(profile=profile, headless=headless) as ctx:
            page = await ctx.new_page()
            await safe_goto(page, base_url)
            await network_settle(page, 1500)

            if save_snaps:
                try:
                    png = await page.screenshot(full_page=True)
                    save_snapshot(f"fullpage_{profile}", await page.content(), png)
                except Exception:
                    pass

            for sc in sections:
                res = await extract_section(page, sc, site_key, profile)
                all_results.extend(res)

    out = TODAY_DIR / "run.jsonl"
    w = JsonlWriter(out)
    for r in all_results:
        w.write(r)
    w.close()

    report = validate(sections, all_results)
    (TODAY_DIR / "health_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    diff = compute_diff(TODAY_DIR)
    (TODAY_DIR / "diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    major = diff.get("ratio_change", 0) >= 0.4
    if report.get("status") == "alert" or major:
        subj = f"[zuza] {site_key}: ALERT"
        body = json.dumps({"health": report, "diff": diff}, ensure_ascii=False, indent=2)
        send_email(subj, body)

def cli_entry():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="rossmann")
    ap.add_argument("--profiles", default="desktop,mobile")
    ap.add_argument("--headless", default="true")
    ap.add_argument("--save-snapshots", default="true")
    args = ap.parse_args()

    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    headless = str(args.headless).lower() in ("1","true","yes")
    save_snaps = str(args.save_snapshots).lower() in ("1","true","yes")

    asyncio.run(run(args.site, profiles, headless, save_snaps))
