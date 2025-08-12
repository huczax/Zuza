def validate(sections_cfg: list[dict], results: list[dict]) -> dict:
    report = {"status": "ok", "sections": []}
    for sc in sections_cfg:
        name = sc.get("name")
        min_count = (sc.get("validation") or {}).get("min_count", 0)
        subset = [r for r in results if r.get("_section") == name]
        ok = len(subset) >= min_count
        report["sections"].append({"name": name, "count": len(subset), "ok": ok})
        if not ok:
            report["status"] = "alert"
    return report
