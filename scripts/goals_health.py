#!/usr/bin/env python3
"""goals_health.py — здоровье целей по ответу yandex_metrika_goals_get (со stats_days).

Классы: dead (мёртвая), noisy (шумная), suspicious_rare (подозрительно редкая макро),
low_data (мало данных), ok. Плюс дубли условий, цели без ценности, «мягкие» цели,
слишком общие URL-условия, нейминг.

Пример:
  python -m scripts.goals_health --input raw/goals.json --visits 41200 \
      --macro-ids 3456 --direct-goal-ids 3455
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from scripts._io import load_json, num

SOFT_TYPES = {"number", "visit_duration"}
LEAD_WORDS = re.compile(r"заявк|заказ|покупк|оплат|lead|order|purchase|checkout|запис|звонок|call", re.I)
GENERIC_URL = {"", "/", "?", "http", "https", ".ru", ".com", "order", "cart", "form"}


def _goals(obj) -> list[dict]:
    if isinstance(obj, dict):
        for k in ("goals", "items"):
            if isinstance(obj.get(k), list):
                return obj[k]
    if isinstance(obj, list):
        return obj
    raise ValueError("не найден список целей")


def _cr(goal: dict, visits: float | None) -> float | None:
    cr = num(goal.get("conversion_rate"))
    if cr is not None:
        return cr / 100.0  # тул отдаёт проценты
    r = num(goal.get("reaches"))
    if r is not None and visits:
        return r / visits
    return None


def _cond_sig(goal: dict) -> str:
    parts = [goal.get("type", "")]
    for c in goal.get("conditions") or []:
        parts.append(f"{c.get('type')}:{(c.get('url') or '').strip().lower()}")
    for s in goal.get("steps") or []:
        parts.append(_cond_sig(s))
    if goal.get("depth"):
        parts.append(f"depth:{goal['depth']}")
    if goal.get("duration"):
        parts.append(f"dur:{goal['duration']}")
    return "|".join(parts)


def classify(goals: list[dict], visits: float | None, macro_ids: set[int],
             direct_ids: set[int], noisy_cr: float = 0.30, noisy_cr_lead: float = 0.15,
             min_visits_dead: float = 500, rare_cr: float = 0.001) -> dict:
    out = []
    sigs: dict[str, list] = {}
    for g in goals:
        gid = g.get("id")
        name = g.get("name") or ""
        reaches = num(g.get("reaches"))
        cr = _cr(g, visits)
        is_macro = gid in macro_ids or bool(LEAD_WORDS.search(name))
        flags = []
        if reaches is None:
            status = "no_stats"
        elif reaches == 0 and (visits or 0) >= min_visits_dead:
            status = "dead"
        elif cr is not None and cr > (noisy_cr_lead if is_macro else noisy_cr):
            status = "noisy"
        elif is_macro and cr is not None and cr < rare_cr and (visits or 0) >= 5000:
            status = "suspicious_rare"
        elif reaches < 10:
            status = "low_data"
        else:
            status = "ok"
        if g.get("type") in SOFT_TYPES:
            flags.append("soft_goal")
            if gid in direct_ids:
                flags.append("soft_goal_in_direct")
        if is_macro and not num(g.get("default_price")):
            flags.append("no_value")
        for c in g.get("conditions") or []:
            if c.get("type") == "contain" and (c.get("url") or "").strip().lower() in GENERIC_URL:
                flags.append("generic_url_condition")
        if re.fullmatch(r"(цель|goal)\s*\d*", name.strip(), re.I) or not name.strip():
            flags.append("bad_name")
        severity = "info"
        if status in ("dead", "noisy") and (gid in direct_ids or gid in macro_ids):
            severity = "critical"
        elif status in ("dead", "noisy", "suspicious_rare") or "soft_goal_in_direct" in flags:
            severity = "major"
        elif flags:
            severity = "minor"
        sigs.setdefault(_cond_sig(g), []).append(gid)
        out.append({"id": gid, "name": name, "type": g.get("type"), "reaches": reaches,
                    "cr": round(cr, 4) if cr is not None else None, "is_macro": is_macro,
                    "in_direct": gid in direct_ids, "status": status, "flags": flags,
                    "severity": severity})
    dups = [ids for ids in sigs.values() if len(ids) > 1]
    summary = {
        "total": len(out),
        "by_status": {s: sum(1 for x in out if x["status"] == s)
                      for s in ("ok", "dead", "noisy", "suspicious_rare", "low_data", "no_stats")},
        "has_macro": any(x["is_macro"] for x in out),
        "has_step_goal": any(x["type"] == "step" for x in out),
        "duplicates": dups,
    }
    return {"summary": summary, "goals": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--visits", type=float, help="визиты за тот же период (для CR и порога мёртвых)")
    ap.add_argument("--macro-ids", default="", help="ID макро-целей через запятую")
    ap.add_argument("--direct-goal-ids", default="", help="ID целей, на которые учится Директ")
    a = ap.parse_args(argv)
    ids = lambda s: {int(x) for x in s.split(",") if x.strip()}
    res = classify(_goals(load_json(a.input)), a.visits, ids(a.macro_ids), ids(a.direct_goal_ids))
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
