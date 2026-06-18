#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
агент лидогенерации (mvp) — эрас диджитал.
ищет публичные контакты бизнесов в нише по открытой базе openstreetmap (overpass api),
квалифицирует, дедуплицирует и выгружает очередь "готово к отправке" в csv.

запуск:
  python3 leadgen.py collect --niche guest_house
  python3 leadgen.py collect --niche guest_house --areas sochi,crimea
конфиг ниши лежит в configs/<niche>.yaml
"""
from __future__ import annotations
import argparse, csv, json, re, sys, time, urllib.request, urllib.parse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("нужен pyyaml: python3 -m pip install pyyaml", file=sys.stderr); raise

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"
OVERPASS = "https://overpass-api.de/api/interpreter"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def overpass_query(tags: list[str], bbox: list[float], limit: int, timeout: int) -> list[dict]:
    # tags вида tourism=guest_house; собираем node+way
    parts = []
    s, w, n, e = bbox
    for tag in tags:
        k, _, v = tag.partition("=")
        sel = f'["{k}"="{v}"]' if v else f'["{k}"]'
        parts.append(f'node{sel}({s},{w},{n},{e});')
        parts.append(f'way{sel}({s},{w},{n},{e});')
    q = f"[out:json][timeout:{timeout}];({''.join(parts)});out center tags {limit};"
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(OVERPASS, data=data, headers={"User-Agent": "eras-leadgen/0.1 (b2b research)"})
    with urllib.request.urlopen(req, timeout=timeout + 30) as r:
        return json.load(r).get("elements", [])


def clean_phone(p: str | None) -> str:
    if not p:
        return ""
    p = p.split(";")[0].strip()
    digits = re.sub(r"[^\d+]", "", p)
    return digits


def clean_site(s: str | None) -> str:
    if not s:
        return ""
    s = s.split(";")[0].strip()
    if s and not s.startswith("http"):
        s = "http://" + s
    return s


def extract_lead(el: dict) -> dict | None:
    t = el.get("tags", {})
    name = t.get("name") or t.get("name:ru")
    if not name:
        return None
    phone = clean_phone(t.get("phone") or t.get("contact:phone") or t.get("mobile"))
    site = clean_site(t.get("website") or t.get("contact:website") or t.get("url"))
    email = (t.get("email") or t.get("contact:email") or "").split(";")[0].strip()
    tg = (t.get("contact:telegram") or "").strip()
    vk = (t.get("contact:vk") or "").strip()
    city = t.get("addr:city") or t.get("addr:town") or ""
    if not (phone or site or email or tg or vk):
        return None  # без единого канала связи лид бесполезен
    return {
        "name": name, "phone": phone, "email": email, "website": site,
        "telegram": tg, "vk": vk, "city": city,
        "osm_id": f"{el.get('type','')[:1]}{el.get('id','')}",
        "lat": el.get("lat") or (el.get("center") or {}).get("lat", ""),
        "lon": el.get("lon") or (el.get("center") or {}).get("lon", ""),
    }


def cmd_collect(args):
    cfg = load_yaml(CONFIG_DIR / f"{args.niche}.yaml")
    tags = cfg["osm_tags"]
    areas = cfg["areas"]
    want = [a.strip() for a in args.areas.split(",")] if args.areas else list(areas.keys())
    limit = args.limit or cfg.get("limit_per_area", 400)
    timeout = cfg.get("overpass_timeout", 60)

    seen, leads = set(), []
    for area in want:
        if area not in areas:
            print(f"  ! район '{area}' не задан в конфиге, пропускаю", file=sys.stderr); continue
        bbox = areas[area]
        print(f"[collect] {args.niche} / {area} ...", file=sys.stderr, flush=True)
        try:
            els = overpass_query(tags, bbox, limit, timeout)
        except Exception as exc:
            print(f"  ! ошибка по району {area}: {exc}", file=sys.stderr); continue
        kept = 0
        for el in els:
            lead = extract_lead(el)
            if not lead or lead["osm_id"] in seen:
                continue
            seen.add(lead["osm_id"])
            lead["area"] = area
            lead["niche"] = args.niche
            leads.append(lead); kept += 1
        print(f"    найдено {len(els)}, с контактами и уникальных: {kept}", file=sys.stderr)
        time.sleep(2)  # вежливо к публичному api

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"leads_{args.niche}.csv"
    cols = ["name", "city", "area", "niche", "phone", "email", "website", "telegram", "vk", "osm_id", "lat", "lon"]
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for l in leads:
            w.writerow({c: l.get(c, "") for c in cols})

    # статистика
    n = len(leads)
    e = sum(1 for l in leads if l["email"])
    p = sum(1 for l in leads if l["phone"])
    s = sum(1 for l in leads if l["website"])
    print(f"\nИТОГО лидов: {n} | с email: {e} | с телефоном: {p} | с сайтом: {s}")
    print(f"файл: {out}")


def main():
    ap = argparse.ArgumentParser(description="агент лидогенерации (mvp)")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("collect", help="собрать лидов по нише")
    c.add_argument("--niche", required=True)
    c.add_argument("--areas", help="через запятую; по умолчанию все из конфига")
    c.add_argument("--limit", type=int, help="лимит на район")
    c.set_defaults(func=cmd_collect)
    args = ap.parse_args()
    if not getattr(args, "cmd", None):
        ap.print_help(); return
    args.func(args)


if __name__ == "__main__":
    main()
