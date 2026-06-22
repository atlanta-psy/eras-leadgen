#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автопостинг тредов в Threads через Publora REST API.
- connections : показать подключённые аккаунты (чтобы узнать id threads)
- post        : разложить треды из файла в отложку по времени
ключ берётся из отдельного файла (key_file в publora.yaml), не из чата.

формат файла тредов (.md):
  цепочки разделяются строкой из === (только ===)
  части внутри одной цепочки — строкой из --- (формат Publora)

запуск:
  python3 publora_post.py connections
  python3 publora_post.py post --file treds.md --dry-run
  python3 publora_post.py post --file treds.md
"""
from __future__ import annotations
import argparse, json, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
API = "https://api.publora.com/api/v1"


def cfg():
    return yaml.safe_load((ROOT / "publora.yaml").read_text(encoding="utf-8"))


def get_key(c) -> str:
    p = (ROOT / c["key_file"]).resolve() if not Path(c["key_file"]).is_absolute() else Path(c["key_file"])
    if not p.exists():
        print(f"нет файла с ключом: {p}\nсоздай его и впиши туда строку sk_...", file=sys.stderr)
        raise SystemExit(1)
    return p.read_text(encoding="utf-8").strip()


def api(method, path, key, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "x-publora-key": key, "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {msg[:300]}")


def cmd_connections(a):
    c = cfg(); key = get_key(c)
    res = api("GET", "/platform-connections", key)
    items = res if isinstance(res, list) else res.get("connections") or res.get("data") or res
    print("подключённые аккаунты:")
    print(json.dumps(items, ensure_ascii=False, indent=2)[:2000])
    print("\nнайди среди них id канала threads (вида 'threads-XXXX') и впиши в publora.yaml -> threads_platform")


def read_chains(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    chains = []
    for block in raw.split("\n==="):
        block = block.strip().strip("=").strip()
        if block:
            chains.append(block)
    return chains


def schedule_times(c, n):
    off = c.get("utc_offset_hours", 3)
    times = c.get("default_times", ["09:00"])
    per_day = c.get("per_day", len(times))
    start = datetime.now(timezone.utc) + timedelta(hours=off)  # локальное «сейчас»
    start = start.replace(second=0, microsecond=0) + timedelta(days=c.get("start_offset_days", 0))
    out = []
    day = 0
    while len(out) < n:
        for t in times[:per_day]:
            hh, mm = map(int, t.split(":"))
            local = (start + timedelta(days=day)).replace(hour=hh, minute=mm)
            if local <= datetime.now(timezone.utc) + timedelta(hours=off):
                continue  # уже прошло сегодня
            utc = local - timedelta(hours=off)
            out.append(utc.strftime("%Y-%m-%dT%H:%M:00.000Z"))
            if len(out) >= n:
                break
        day += 1
        if day > 60:
            break
    return out


def cmd_post(a):
    c = cfg()
    plat = c.get("threads_platform", "").strip()
    if not plat and not a.dry_run:
        print("сначала узнай id threads: python3 publora_post.py connections, впиши в publora.yaml", file=sys.stderr)
        raise SystemExit(1)
    chains = read_chains(Path(a.file))
    times = schedule_times(c, len(chains))
    print(f"тредов к публикации: {len(chains)}" + (" [ПРОБНЫЙ ПРОГОН]" if a.dry_run else ""))
    key = None if a.dry_run else get_key(c)
    for i, (chain, when) in enumerate(zip(chains, times), 1):
        parts = chain.count("\n---") + 1
        first = chain.splitlines()[0][:60]
        if a.dry_run:
            print(f"  {i}. {when} · частей: {parts} · «{first}…»")
            continue
        body = {"content": chain, "platforms": [plat], "scheduledTime": when}
        try:
            res = api("POST", "/create-post", key, body)
            print(f"  {i}. поставлено на {when} · частей {parts} · id {res.get('postGroupId', res)}")
        except Exception as exc:
            print(f"  {i}. ! ошибка: {exc}", file=sys.stderr)
    if a.dry_run:
        print("это был пробный прогон — ничего не отправлено. убери --dry-run для реальной постановки.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("connections")
    p = sub.add_parser("post"); p.add_argument("--file", required=True); p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "connections": cmd_connections(a)
    elif a.cmd == "post": cmd_post(a)
    else: ap.print_help()


if __name__ == "__main__":
    main()
