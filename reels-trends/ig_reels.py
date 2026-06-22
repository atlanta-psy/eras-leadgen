#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reels-разведка по нише через Apify (Instagram).
Берёт reels по хэштегам, считает вовлечённость, выдаёт ранжированную выборку залетевшего.

запуск:
  python3 ig_reels.py            # по config.yaml (нужен токен Apify)
  python3 ig_reels.py --self-test # проверить разбор без сети/токена
"""
from __future__ import annotations
import argparse, csv, json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent


def apify_run(actor: str, token: str, payload: dict, timeout: int = 600) -> list:
    url = f"https://api.apify.com/v2/acts/{actor.replace('/', '~')}/run-sync-get-dataset-items?token={token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def to_date(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    except Exception:
        return None


def extract_post(it: dict) -> dict | None:
    typ = it.get("type") or ""
    pt = it.get("productType") or ""
    fmt = "рилс" if (typ == "Video" or pt == "clips") else ("карусель" if typ == "Sidecar" else "фото")
    likes = it.get("likesCount") or 0
    if likes < 0:   # инстаграм скрыл лайки (часто у каруселей) -> считаем неизвестным
        likes = 0
    comments = max(it.get("commentsCount") or 0, 0)
    views = max(it.get("videoPlayCount") or it.get("videoViewCount") or 0, 0)
    cap = " ".join((it.get("caption") or "").split())
    url = it.get("url") or (f"https://www.instagram.com/p/{it.get('shortCode')}/" if it.get("shortCode") else "")
    d = to_date(it.get("timestamp"))
    return {"format": fmt, "caption": cap[:160], "owner": it.get("ownerUsername") or "",
            "likes": likes, "comments": comments, "views": views, "engagement": likes + comments,
            "date": d.isoformat() if d else "", "url": url, "source": it.get("_src", "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--max-fetch", type=int, default=999, help="сколько НОВЫХ профилей тянуть за запуск (для обхода лимита времени)")
    ap.add_argument("--refresh", action="store_true", help="перетянуть всё заново, игнорируя кэш")
    a = ap.parse_args()

    if a.self_test:
        sample = [
            {"type": "Video", "shortCode": "Cxyz", "caption": "как перестать угождать всем 3 шага",
             "likesCount": 12000, "commentsCount": 340, "videoPlayCount": 410000,
             "timestamp": "2026-06-10T10:00:00.000Z", "ownerUsername": "psy.blog"},
            {"type": "Image", "shortCode": "Cabc", "caption": "просто фото", "likesCount": 50, "commentsCount": 2},
        ]
        out = [extract_post(x) for x in sample]
        out = [x for x in out if x]
        print("self-test: постов распознано", len(out))
        for x in out:
            print(f"  {x['format']} · {x['views']:,} просм · {x['likes']:,} лайк · вовл {x['engagement']:,} · @{x['owner']} · {x['caption']}")
        return

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if "ВСТАВЬ" in cfg.get("apify_token", ""):
        print("впиши токен Apify в config.yaml", file=sys.stderr); return
    today = datetime.now(timezone.utc).date()

    rows = []
    profiles = [p.strip().lstrip("@") for p in (cfg.get("profiles") or []) if p and "example" not in p]
    if profiles:
        mode = "профили"
        cache_dir = ROOT / "cache"; cache_dir.mkdir(exist_ok=True)
        fetched = 0
        for u in profiles:
            cf = cache_dir / f"{u}.json"
            if cf.exists() and not a.refresh:
                items = json.loads(cf.read_text(encoding="utf-8"))
                src_note = "кэш"
            elif fetched >= a.max_fetch:
                continue  # лимит новых на этот запуск исчерпан — обработаем в следующий
            else:
                print(f"[ig] @{u} (тяну) ...", file=sys.stderr, flush=True)
                try:
                    items = apify_run(cfg.get("profile_actor", "apify/instagram-scraper"), cfg["apify_token"],
                                      {"directUrls": [f"https://www.instagram.com/{u}/"],
                                       "resultsType": "posts", "resultsLimit": cfg.get("results_limit", 30)})
                except Exception as exc:
                    print(f"  ! @{u}: {exc}", file=sys.stderr); continue
                cf.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
                fetched += 1; src_note = "новое"
            kept = 0
            for it in items:
                it["_src"] = "@" + u
                r = extract_post(it)
                if not r or r["engagement"] < cfg.get("min_likes", 0):
                    continue
                d = to_date(it.get("timestamp"))
                if d and cfg.get("max_age_days") and (today - d).days > cfg["max_age_days"]:
                    continue
                rows.append(r); kept += 1
            print(f"  @{u}: {kept} ({src_note})", file=sys.stderr)
    else:
        mode = "хэштеги"
        for tag in cfg.get("hashtags", []):
            print(f"[ig] #{tag} ...", file=sys.stderr, flush=True)
            try:
                items = apify_run(cfg["actor"], cfg["apify_token"],
                                  {"hashtags": [tag], "resultsLimit": cfg.get("results_limit", 50)})
            except Exception as exc:
                print(f"  ! #{tag}: {exc}", file=sys.stderr); continue
            for it in items:
                it["_src"] = "#" + tag
                r = extract_post(it)
                if not r or r["engagement"] < cfg.get("min_likes", 0):
                    continue
                d = to_date(it.get("timestamp"))
                if d and cfg.get("max_age_days") and (today - d).days > cfg["max_age_days"]:
                    continue
                rows.append(r)

    seen, uniq = set(), []
    for r in sorted(rows, key=lambda x: x["engagement"], reverse=True):
        if r["url"] in seen:
            continue
        seen.add(r["url"]); uniq.append(r)
    top = uniq[: cfg.get("top", 25)]

    md = ROOT / f"reels-разведка-{today}.md"
    L = [f"# Instagram-разведка по нише — {today}\n",
         f"режим: {mode} · подходящих постов: {len(uniq)} · в отчёте топ-{len(top)}\n",
         "## залетевшее (по вовлечённости: лайки + комменты)\n"]
    for i, r in enumerate(top, 1):
        vv = f" · просмотры {r['views']:,}" if r["views"] else ""
        L.append(f"{i}. [{r['format']}] **{r['caption'] or '(без подписи)'}**")
        L.append(f"   {r['source']} · лайки {r['likes']:,} · комменты {r['comments']:,}{vv} · {r['date']}")
        L.append(f"   {r['url']}")
    L.append("\n## как читать\n— это лучшие посты сильных авторов ниши за период. бери формат (рилс/карусель), хук и тему — адаптируй под свой голос.")
    md.write_text("\n".join(L), encoding="utf-8")

    cpath = ROOT / f"reels-разведка-{today}.csv"
    with cpath.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["format", "caption", "owner", "likes", "comments", "views", "engagement", "date", "source", "url"])
        for r in top:
            w.writerow([r["format"], r["caption"], r["owner"], r["likes"], r["comments"], r["views"], r["engagement"], r["date"], r["source"], r["url"]])
    print(f"готово ({mode}):\n  {md}\n  {cpath}")


if __name__ == "__main__":
    main()
