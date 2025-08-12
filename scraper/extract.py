from loguru import logger
from .utils import pick_best_from_srcset

async def _locate_root(page, input_cfg: dict):
    if not input_cfg: return None
    t, v = input_cfg.get("type"), input_cfg.get("value")
    if t == "css":   return page.locator(v)
    if t == "xpath": return page.locator(f"xpath={v}")
    if t == "text":
        el = page.get_by_text(v).first
        return el.locator("xpath=ancestor-or-self::section[1]")
    return None

async def _extract_fields(scope, fields_cfg: list[dict]):
    out = {}
    for f in fields_cfg:
        name, ftype, sel, attr = f.get("name"), f.get("type"), f.get("selector"), f.get("attr")
        node = scope if sel == ":self" else scope.locator(sel)
        try:
            if ftype in ("text","text_optional"):
                txt = await node.first.inner_text()
                out[name] = txt.strip()
            elif ftype == "attr":
                out[name] = await node.first.get_attribute(attr)
            elif ftype == "image":
                out[name] = await node.first.get_attribute(attr or "src")
            elif ftype == "srcset":
                srcset = await node.first.get_attribute(attr or "srcset")
                out[name] = pick_best_from_srcset(srcset)
        except Exception:
            if ftype != "text_optional":
                out[name] = None
    return out

async def extract_section(page, section_cfg: dict, site_key: str, profile: str):
    root = await _locate_root(page, section_cfg.get("input"))
    if root is None:
        logger.warning(f"Root not found for {section_cfg.get('name')}")
        return []
    items_sel = (section_cfg.get("list") or {}).get("item_selector")
    if items_sel:
        items = root.locator(items_sel)
        count = await items.count()
        results = []
        for i in range(count):
            node = items.nth(i)
            rec = await _extract_fields(node, section_cfg.get("list", {}).get("fields", []))
            rec.update({"_section": section_cfg.get("name"), "_idx": i, "_profile": profile})
            results.append(rec)
        return results
    else:
        rec = await _extract_fields(root, section_cfg.get("fields", []))
        rec.update({"_section": section_cfg.get("name"), "_profile": profile})
        return [rec]
