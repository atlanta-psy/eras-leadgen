#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
источник ВКонтакте: находит сообщества бизнесов в нише и тянет их контакты
(сайт, телефон, email, ссылку на сообщество) через VK API. Сливает в общую базу
data/leads_<niche>.csv с дедупом.

запуск:
  python3 vk_collect.py --niche guest_house             # собрать по конфигу
  python3 vk_collect.py --niche guest_house --self-test  # проверить парсер без сети
конфиг: configs/<niche>_vk.yaml (нужен бесплатный токен ВК — инструкция в конфиге)
"""
from __future__ import annotations
import argparse, csv, json, re, sys, time, urllib.request, urllib.parse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs"
DATA = ROOT / "data"
API = "https://api.vk.com/method/"
COLS = ["name", "city", "area", "niche", "phone", "email", "website", "telegram", "vk", "osm_id", "lat", "lon"]


def clean_phone(p: str) -> str:
    return re.sub(r"[^\d+]", "", (p or "").split(",")[0])


def vk_call(method: str, params: dict) -> dict:
    url = API + method + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "eras-leadgen/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "error" in data:
        raise RuntimeError("VK: " + data["error"].get("error_msg", str(data["error"])))
    return data["response"]


def groups_from_getbyid(resp) -> list:
    # v5.199 возвращает {"groups":[...]}, старые — просто список
    if isinstance(resp, dict) and "groups" in resp:
        return resp["groups"]
    return resp if isinstance(resp, list) else []


def extract_group(g: dict, city: str, niche: str) -> dict | None:
    name = g.get("name")
    if not name:
        return None
    phone = email = ""
    for c in g.get("contacts", []) or []:
        if c.get("phone") and not phone:
            phone = clean_phone(c["phone"])
        if c.get("email") and not email:
            email = c["email"].strip()
    site = (g.get("site") or "").strip()
    screen = g.get("screen_name") or (f"club{g.get('id')}" if g.get("id") else "")
    vk_link = f"vk.com/{screen}" if screen else ""
    if not (phone or email or site or vk_link):
        return None
    return {"name": name, "city": city, "area": city, "niche": niche,
            "phone": phone, "email": email, "website": site,
            "telegram": "", "vk": vk_link, "osm_id": "vk" + str(g.get("id", "")),
            "lat": "", "lon": ""}


def load_existing(path: Path):
    rows, keys = [], set()
    if path.exists():
        for r in csv.DictReader(path.open(encoding="utf-8-sig")):
            rows.append(r)
            keys.add((r.get("phone") or "") or (r.get("vk") or "") or (r.get("name") or "").lower())
    return rows, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche", required=True)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sample_groups = [
            {"id": 111, "name": "Гостевой дом «Морской бриз»", "screen_name": "morskoybriz_sochi",
             "site": "http://morskoybriz.ru", "contacts": [{"phone": "+7 988 111-22-33", "email": "briz@mail.ru"}]},
            {"id": 222, "name": "Сообщество без контактов", "screen_name": "noinfo", "contacts": []},
        ]
        out = [extract_group(g, "Сочи", a.niche) for g in sample_groups]
        out = [x for x in out if x]
        print("self-test: распознано", len(out), "из 2")
        for x in out:
            print("  ", x["name"], "|", x["phone"], "|", x["email"], "|", x["website"], "|", x["vk"])
        return

    cfg = yaml.safe_load((CONFIG / f"{a.niche}_vk.yaml").read_text(encoding="utf-8"))
    if "ВСТАВЬ" in cfg.get("access_token", ""):
        print("впиши токен ВК в configs/%s_vk.yaml (инструкция там же)" % a.niche, file=sys.stderr); return
    tok, ver = cfg["access_token"], cfg.get("api_version", "5.199")

    path = DATA / f"leads_{a.niche}.csv"
    rows, keys = load_existing(path)
    before = len(rows)
    added = 0
    for city in cfg["cities"]:
        print(f"[vk] {city} ...", file=sys.stderr, flush=True)
        try:
            found = vk_call("groups.search", {"q": f"{cfg['query']} {city}", "count": cfg.get("per_city", 100),
                                              "access_token": tok, "v": ver})
            ids = [str(it["id"]) for it in found.get("items", []) if it.get("id")]
        except Exception as exc:
            print(f"  ! поиск по {city}: {exc}", file=sys.stderr); break
        # детали пачками по ics 500
        for i in range(0, len(ids), 200):
            chunk = ",".join(ids[i:i + 200])
            try:
                resp = vk_call("groups.getById", {"group_ids": chunk, "fields": "site,contacts,description,city",
                                                  "access_token": tok, "v": ver})
            except Exception as exc:
                print(f"  ! детали {city}: {exc}", file=sys.stderr); continue
            for g in groups_from_getbyid(resp):
                lead = extract_group(g, city, a.niche)
                if not lead:
                    continue
                k = (lead["phone"] or "") or lead["vk"] or lead["name"].lower()
                if k in keys:
                    continue
                keys.add(k); rows.append(lead); added += 1
            time.sleep(0.34)  # лимит VK ~3 запроса/сек

    DATA.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"\nВК добавил {added} новых лидов. было {before}, стало {len(rows)}.")
    print(f"файл: {path}")


if __name__ == "__main__":
    main()
