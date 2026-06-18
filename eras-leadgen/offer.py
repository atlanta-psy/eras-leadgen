#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
генератор офферов: на каждого лида — холодное первое сообщение + короткий текст КП.
голос Педро (от первого лица «я»), без выдуманных цифр, цена «обсуждаемо».

запуск:
  python3 offer.py --niche guest_house                 # для всех лидов -> data/outreach_<niche>.csv
  python3 offer.py --niche guest_house --name "Оливия" --print   # один лид в консоль
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def first_name_clean(name: str) -> str:
    return (name or "").strip().strip('"«»')


def build_message(lead: dict, off: dict) -> str:
    """холодное первое сообщение: коротко, без ссылки, цель — получить ответ."""
    name = first_name_clean(lead["name"])
    city = lead.get("city") or ""
    where = f" в {city}" if city else ""
    has_site = bool(lead.get("website"))
    if lead.get("has_booking") == "yes":
        empathy = off["msg_empathy_booking"]
    elif has_site:
        empathy = off["msg_empathy_site"]
    else:
        empathy = off["msg_empathy_nosite"]
    return (
        f"Здравствуйте! Пишу вам по гостевому дому «{name}»{where}. {off['msg_who']}\n\n"
        f"{empathy}\n\n"
        f"{off['msg_case']}\n\n"
        f"{off['msg_cta']}\n\n"
        f"— {off['signature']}"
    )


def build_subject(lead: dict, off: dict) -> str:
    return off["subject"].format(name=first_name_clean(lead["name"]))


def build_followups(off: dict) -> tuple[str, str]:
    return off["followup1"], off["followup2"]


def build_kp(lead: dict, off: dict) -> str:
    """короткий текст КП (этап текста, без pdf) — по структуре скила kp-eras."""
    name = first_name_clean(lead["name"])
    pains = off["pains_with_site"] if lead.get("website") else off["pains_no_site"]
    L = []
    L.append(f"Гостевой дом «{name}»: прямые брони без комиссии агрегаторов\n")
    L.append("Вы сдаёте номера — а зарабатывают на этом агрегаторы. Я возвращаю брони и гостя вам.\n")
    L.append("Что я вижу:")
    for p in pains:
        L.append(f"— {p}")
    L.append("")
    L.append("Что предлагаю:")
    for b in off["offer_blocks"]:
        L.append(f"— {b}")
    L.append("")
    L.append("Что вы получаете:")
    for o in off["outcomes"]:
        L.append(f"— {o}")
    L.append("")
    cap = lambda s: s[:1].upper() + s[1:]
    L.append(cap(off['case_line']))
    L.append(f"{cap(off['time_delay'])}. {cap(off['effort'])}.")
    L.append(f"Цена — {off['price_line']}.")
    L.append("")
    L.append(f"Что дальше: {off['pilot_text']}. {cap(off['promo_urgency'])}.")
    L.append(f"Напишите в телеграм {off['contact_tg']} или ответьте на это письмо — "
             f"согласую функции и пришлю точную смету.")
    L.append("")
    L.append(f"— {off['signature']}")
    L.append(f"{off['contact_site']} · телеграм/max {off['contact_phone']}")
    return "\n".join(L)


def cmd(args):
    off = load_yaml(CONFIG_DIR / f"{args.niche}_offer.yaml")
    enriched = DATA_DIR / f"leads_{args.niche}_enriched.csv"
    src = enriched if enriched.exists() else (DATA_DIR / f"leads_{args.niche}.csv")
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    for r in rows:  # подставляем найденные на сайте контакты, если своих не было
        if not r.get("email") and r.get("email_found"):
            r["email"] = r["email_found"]
        if not r.get("telegram") and r.get("tg_found"):
            r["telegram"] = r["tg_found"]
        if not r.get("vk") and r.get("vk_found"):
            r["vk"] = r["vk_found"]
    if args.name:
        rows = [r for r in rows if args.name.lower() in (r.get("name") or "").lower()]
        if not rows:
            print("лид не найден", file=sys.stderr); return

    if args.print:
        for r in rows[:1]:
            print("====== ТЕМА ПИСЬМА ======\n")
            print(build_subject(r, off))
            print("\n====== ХОЛОДНОЕ СООБЩЕНИЕ ======\n")
            print(build_message(r, off))
            f1, f2 = build_followups(off)
            print("\n====== ФОЛЛОУ-АП 1 (через 3-4 дня) ======\n")
            print(f1)
            print("\n====== ФОЛЛОУ-АП 2 (через неделю) ======\n")
            print(f2)
            print("\n====== КОРОТКОЕ КП (после ответа «да») ======\n")
            print(build_kp(r, off))
        return

    out = DATA_DIR / f"outreach_{args.niche}.csv"
    cols = ["name", "city", "channel", "email", "phone", "telegram", "vk", "website",
            "has_booking", "subject", "message", "followup1", "followup2", "kp_text", "status"]
    f1, f2 = build_followups(off)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            channel = "email" if r.get("email") else ("telegram" if r.get("telegram") else ("vk" if r.get("vk") else "phone"))
            w.writerow({
                "name": r["name"], "city": r.get("city", ""), "channel": channel,
                "email": r.get("email", ""), "phone": r.get("phone", ""),
                "telegram": r.get("telegram", ""), "vk": r.get("vk", ""), "website": r.get("website", ""),
                "has_booking": r.get("has_booking", ""),
                "subject": build_subject(r, off), "message": build_message(r, off),
                "followup1": f1, "followup2": f2, "kp_text": build_kp(r, off), "status": "new",
            })
    print(f"очередь готова: {out} ({len(rows)} офферов)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche", required=True)
    ap.add_argument("--name", help="сгенерить для одного лида по имени")
    ap.add_argument("--print", action="store_true", help="вывести в консоль, не писать csv")
    ap.set_defaults(func=cmd)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
