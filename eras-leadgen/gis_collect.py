#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
источник 2ГИС: добирает лидов через Catalog API 2ГИС и сливает в общую базу
data/leads_<niche>.csv (с дедупом по телефону/названию).

запуск:
  python3 gis_collect.py --niche guest_house            # собрать по конфигу
  python3 gis_collect.py --niche guest_house --self-test # проверить парсер без сети
конфиг: configs/<niche>_gis.yaml (нужен бесплатный ключ 2ГИС)
"""
from __future__ import annotations
import argparse, csv, json, re, sys, time, urllib.request, urllib.parse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs"
DATA = ROOT / "data"
API = "https://catalog.api.2gis.com/3.0/items"
COLS = ["name", "city", "area", "niche", "phone", "email", "website", "telegram", "vk", "osm_id", "lat", "lon"]


def clean_phone(p: str) -> str:
    return re.sub(r"[^\d+]", "", (p or "").split(",")[0])


def extract_item(it: dict, city: str, niche: str) -> dict | None:
    name = it.get("name") or it.get("name_ex", {}).get("primary")
    if not name:
        return None
    phone = email = website = ""
    for g in it.get("contact_groups", []):
        for c in g.get("contacts", []):
            t = c.get("type")
            val = c.get("value") or c.get("url") or c.get("text") or ""
            if t == "phone" and not phone:
                phone = clean_phone(val)
            elif t == "email" and not email:
                email = val.strip()
            elif t in ("website", "url") and not website:
                website = val.strip()
    if not (phone or email or website):
        return None
    pt = it.get("point", {}) or {}
    return {"name": name, "city": city, "area": city, "niche": niche,
            "phone": phone, "email": email, "website": website,
            "telegram": "", "vk": "", "osm_id": "gis" + str(it.get("id", "")),
            "lat": pt.get("lat", ""), "lon": pt.get("lon", "")}


def fetch_page(key: str, query: str, city: str, page: int, page_size: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": f"{query} {city}", "page": page, "page_size": page_size,
        "fields": "items.point,items.contact_groups", "key": key,
    })
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "eras-leadgen/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    meta = data.get("meta", {})
    if meta.get("code") and meta["code"] != 200:
        raise RuntimeError(f"2ГИС: {meta.get('error', {}).get('message', meta['code'])}")
    return data.get("result", {}).get("items", [])


def load_existing(path: Path) -> tuple[list[dict], set]:
    rows, keys = [], set()
    if path.exists():
        for r in csv.DictReader(path.open(encoding="utf-8-sig")):
            rows.append(r)
            keys.add((r.get("phone") or "") or (r.get("name") or "").lower())
    return rows, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche", required=True)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sample = {"result": {"items": [
            {"id": "70000001", "name": "Гостевой дом Ромашка",
             "point": {"lat": 43.6, "lon": 39.7},
             "contact_groups": [{"contacts": [
                 {"type": "phone", "value": "+7 999 000-00-00"},
                 {"type": "email", "value": "romashka@mail.ru"},
                 {"type": "website", "value": "http://romashka-sochi.ru"}]}]},
            {"id": "70000002", "name": "Без контактов", "contact_groups": []},
        ]}}
        out = [extract_item(it, "Сочи", a.niche) for it in sample["result"]["items"]]
        out = [x for x in out if x]
        print("self-test: распарсено", len(out), "из 2 (второй без контактов отсеян)")
        for x in out:
            print("  ", x["name"], "|", x["phone"], "|", x["email"], "|", x["website"])
        return

    cfg = yaml.safe_load((CONFIG / f"{a.niche}_gis.yaml").read_text(encoding="utf-8"))
    if "ВСТАВЬ" in cfg.get("api_key", ""):
        print("впиши ключ 2ГИС в configs/%s_gis.yaml" % a.niche, file=sys.stderr); return

    path = DATA / f"leads_{a.niche}.csv"
    rows, keys = load_existing(path)
    before = len(rows)
    added = 0
    for city in cfg["cities"]:
        print(f"[2gis] {city} ...", file=sys.stderr, flush=True)
        for page in range(1, cfg.get("max_pages", 10) + 1):
            try:
                items = fetch_page(cfg["api_key"], cfg["query"], city, page, cfg.get("page_size", 50))
            except Exception as exc:
                print(f"  ! {city} стр.{page}: {exc}", file=sys.stderr); break
            if not items:
                break
            for it in items:
                lead = extract_item(it, city, a.niche)
                if not lead:
                    continue
                k = (lead["phone"] or "") or lead["name"].lower()
                if k in keys:
                    continue
                keys.add(k); rows.append(lead); added += 1
            time.sleep(0.3)

    DATA.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"\n2ГИС добавил {added} новых лидов. было {before}, стало {len(rows)}.")
    print(f"файл: {path}")


if __name__ == "__main__":
    main()
