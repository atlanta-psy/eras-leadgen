#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
обогащение лидов: дедуп + отсев мусора + заход на сайт.
с сайта тянем: email (если не было), есть ли уже онлайн-бронирование,
платформу сайта и короткую деталь для персонализации.

запуск:
  python3 enrich.py --niche guest_house            # все
  python3 enrich.py --niche guest_house --limit 10 # первые 10 (для теста)
"""
from __future__ import annotations
import argparse, csv, re, sys, time, urllib.request, gzip, io
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TME_RE = re.compile(r"(?:https?:)?//t\.me/([A-Za-z0-9_]{3,})", re.I)
VK_RE = re.compile(r"(?:https?:)?//(?:m\.)?vk\.(?:com|ru)/([A-Za-z0-9_.]{2,})", re.I)
TG_SKIP = {"share", "joinchat", "iv", "s", "addstickers", "proxy"}
VK_SKIP = {"share", "widget", "away", "video_ext", "js", "share.php", "im"}
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)

BOOKING_SIGNALS = ["онлайн-брон", "забронир", "bnovo", "travelline", "realtycalendar",
                   "шахматк", "модуль брон", "выбрать даты", "календарь свобод",
                   "book online", "reservation", "/booking", "забронировать онлайн"]
PLATFORMS = {"tilda": "Tilda", "wix.com": "Wix", "nethouse": "Nethouse",
             "bitrix": "1С-Битрикс", "wordpress": "WordPress", "wp-content": "WordPress",
             "ukit": "uKit", "creatium": "Creatium"}
JUNK_EMAIL = ("example.com", "sentry", "wixpress", "tilda", "domain.com", ".png", ".jpg",
              "vk-portal", "stacks", "@2x", "yandex.ru/maps", "u00", "noreply", "no-reply")


def norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip(' "«»'))


def fetch(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; eras-leadgen/0.2)",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    for enc in ("utf-8", "windows-1251"):
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def enrich_one(lead: dict) -> dict:
    site = lead.get("website") or ""
    out = {"email_found": "", "tg_found": "", "vk_found": "", "has_booking": "", "platform": "", "site_title": "", "site_ok": ""}
    if not site:
        return out
    try:
        html = fetch(site)
        out["site_ok"] = "1"
    except Exception as exc:
        out["site_ok"] = f"err:{type(exc).__name__}"
        return out
    low = html.lower()
    # email
    if not lead.get("email"):
        for m in EMAIL_RE.findall(html):
            if not any(j in m.lower() for j in JUNK_EMAIL):
                out["email_found"] = m
                break
    # соцсети для личных сообщений
    for h in TME_RE.findall(html):
        if h.lower() not in TG_SKIP:
            out["tg_found"] = "@" + h; break
    for h in VK_RE.findall(html):
        if h.lower() not in VK_SKIP and not h.lower().endswith(".php"):
            out["vk_found"] = "vk.com/" + h; break
    # booking signal
    out["has_booking"] = "yes" if any(sig in low for sig in BOOKING_SIGNALS) else "no"
    # platform
    for key, label in PLATFORMS.items():
        if key in low:
            out["platform"] = label
            break
    # title / desc для персонализации
    t = TITLE_RE.search(html)
    d = DESC_RE.search(html)
    out["site_title"] = clean(t.group(1))[:140] if t else (clean(d.group(1))[:140] if d else "")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche", required=True)
    ap.add_argument("--limit", type=int, help="ограничить число лидов (для теста)")
    a = ap.parse_args()

    rows = list(csv.DictReader((DATA / f"leads_{a.niche}.csv").open(encoding="utf-8-sig")))

    # --- дедуп + отсев мусора ---
    seen_key, clean_rows, dropped = set(), [], 0
    for r in rows:
        nm = norm_name(r.get("name"))
        key = (r.get("email") or "").lower() or nm  # дубль по email, иначе по имени
        if key in seen_key:
            dropped += 1; continue
        if not (r.get("phone") or r.get("email") or r.get("website")):
            dropped += 1; continue
        seen_key.add(key)
        clean_rows.append(r)
    print(f"[qualify] было {len(rows)}, после дедупа/отсева {len(clean_rows)} (убрано {dropped})", file=sys.stderr)

    todo = clean_rows[: a.limit] if a.limit else clean_rows
    enriched = []
    for i, r in enumerate(todo, 1):
        e = enrich_one(r)
        r.update(e)
        enriched.append(r)
        flag = "БРОНЬ ЕСТЬ" if e["has_booking"] == "yes" else ("нет брони" if e["has_booking"] == "no" else "сайт недоступен")
        print(f"  [{i}/{len(todo)}] {r['name'][:32]:32} | {flag} | {e.get('email_found') or r.get('email') or '—'}", file=sys.stderr)
        if r.get("website"):
            time.sleep(0.5)

    # дописываем необогащённый хвост (если был --limit)
    rest = clean_rows[len(todo):]
    out = DATA / f"leads_{a.niche}_enriched.csv"
    base_cols = ["name", "city", "area", "niche", "phone", "email", "website", "telegram", "vk", "osm_id", "lat", "lon"]
    extra = ["email_found", "tg_found", "vk_found", "has_booking", "platform", "site_title", "site_ok"]
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=base_cols + extra)
        w.writeheader()
        for r in enriched + rest:
            w.writerow({c: r.get(c, "") for c in base_cols + extra})

    nb = sum(1 for r in enriched if r.get("has_booking") == "yes")
    nm = sum(1 for r in enriched if r.get("email_found"))
    ntg = sum(1 for r in enriched if r.get("tg_found"))
    nvk = sum(1 for r in enriched if r.get("vk_found"))
    print(f"\nобогащено: {len(enriched)} | уже с бронированием: {nb} | новых email: {nm} | телеграм со сайтов: {ntg} | вк со сайтов: {nvk}")
    print(f"файл: {out}")


if __name__ == "__main__":
    main()
