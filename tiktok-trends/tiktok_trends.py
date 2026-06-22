#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok-разведка по нише (бесплатно, через yt-dlp).
Берёт свежие ролики выбранных аккаунтов, метрики и вовлечённость,
выдаёт ранжированную выборку залетевшего для адаптации.

запуск:
  python3 tiktok_trends.py            # по accounts.yaml
требует установленного yt-dlp (pip install yt-dlp).
"""
from __future__ import annotations
import json, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
YTDLP = shutil.which("yt-dlp") or "yt-dlp"


def run(args, timeout):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def flat_list(account: str, limit: int, timeout: int = 60) -> list[dict]:
    url = f"https://www.tiktok.com/{account}" if account.startswith("@") else account
    r = run([YTDLP, "--no-warnings", "--flat-playlist", "--playlist-end", str(limit), "--dump-json", url], timeout)
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def full_meta(url: str, timeout: int = 40) -> dict:
    r = run([YTDLP, "--no-warnings", "--dump-json", url], timeout)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def date_from_id(vid: str):
    # id тиктока кодирует время в старших битах
    try:
        ts = int(vid) >> 32
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    except Exception:
        return None


def main():
    cfg = yaml.safe_load((ROOT / "accounts.yaml").read_text(encoding="utf-8"))
    accounts = [a for a in cfg["accounts"] if "example" not in a]
    if not accounts:
        print("впиши реальные аккаунты в accounts.yaml (убери example)", file=sys.stderr); return
    today = datetime.now(timezone.utc).date()

    cand = []
    for acc in accounts:
        print(f"[tiktok] {acc} ...", file=sys.stderr, flush=True)
        try:
            entries = flat_list(acc, cfg.get("per_account", 25))
        except subprocess.TimeoutExpired:
            print(f"  ! таймаут по {acc}", file=sys.stderr); continue
        kept = 0
        for e in entries:
            vid = str(e.get("id") or "")
            views = e.get("view_count") or 0
            if views < cfg.get("min_views", 0):
                continue
            d = date_from_id(vid)
            if d and cfg.get("max_age_days") and (today - d).days > cfg["max_age_days"]:
                continue
            cand.append({"account": acc, "id": vid, "title": (e.get("title") or "").strip(),
                         "views": views, "url": e.get("url") or f"https://www.tiktok.com/{acc}/video/{vid}",
                         "date": d.isoformat() if d else ""})
            kept += 1
        print(f"    подходящих: {kept}", file=sys.stderr)
        time.sleep(0.5)

    cand.sort(key=lambda x: x["views"], reverse=True)
    top = cand[: cfg.get("top_full", 15)]
    # добираем лайки/комменты для топа
    for c in top:
        m = full_meta(c["url"])
        likes = m.get("like_count") or 0
        comments = m.get("comment_count") or 0
        reposts = m.get("repost_count") or 0
        c["likes"], c["comments"], c["reposts"] = likes, comments, reposts
        c["er"] = round((likes + comments + reposts) / max(c["views"], 1) * 100, 1)
        time.sleep(0.4)

    # отчёт
    out = ROOT / f"tiktok-разведка-{today.isoformat()}.md"
    L = [f"# TikTok-разведка по нише — {today.isoformat()}\n",
         f"аккаунтов: {len(accounts)} · подходящих роликов: {len(cand)} · в разборе топ-{len(top)}\n",
         "## залетевшие ролики (по просмотрам, с вовлечённостью)\n"]
    for i, c in enumerate(top, 1):
        L.append(f"{i}. **{c['title'][:80] or '(без подписи)'}**")
        L.append(f"   {c['account']} · просмотры: {c['views']:,} · лайки: {c.get('likes',0):,} · "
                 f"комменты: {c.get('comments',0):,} · вовлечённость: {c.get('er','—')}% · {c['date']}")
        L.append(f"   {c['url']}")
    L.append("\n## как читать")
    L.append("— высокие просмотры = тема/хук залетели; высокая вовлечённость (ER) = ролик реально цепляет, а не просто попал в показы.")
    L.append("— бери заголовок/хук и первый кадр, адаптируй под свой голос и формат.")
    (out).write_text("\n".join(L), encoding="utf-8")

    # csv
    import csv
    cpath = ROOT / f"tiktok-разведка-{today.isoformat()}.csv"
    with cpath.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["title", "account", "views", "likes", "comments", "reposts", "ER%", "date", "url"])
        for c in top:
            w.writerow([c["title"], c["account"], c["views"], c.get("likes", 0), c.get("comments", 0),
                        c.get("reposts", 0), c.get("er", ""), c["date"], c["url"]])
    print(f"готово:\n  {out}\n  {cpath}")


if __name__ == "__main__":
    main()
