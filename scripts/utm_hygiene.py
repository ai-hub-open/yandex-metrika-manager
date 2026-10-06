#!/usr/bin/env python3
"""utm_hygiene.py — гигиена UTM-разметки по отчёту Метрики (R5).

Находит: варианты написания одного источника (регистр, пробелы, алиасы),
нестандартные utm_medium, неподставленные макросы ({campaign_id}),
долю визитов без utm_source.

Пример:
  python -m scripts.utm_hygiene --input raw/04_utm.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from scripts._io import load_table, num

STANDARD_MEDIUM = {"cpc", "cpm", "cpa", "cpv", "email", "social", "referral", "organic", "banner",
                   "display", "messenger", "push", "sms", "influencer", "partner", "affiliate",
                   "video", "retargeting", "smm", "paid_social", "qr", "offline"}
ALIASES = {
    "yandex": {"yandex", "ya", "яндекс", "yandex.direct", "yandexdirect", "direct", "yd", "yandex_direct"},
    "vk": {"vk", "vkontakte", "вк", "vk.com", "vkads", "vk_ads", "mytarget"},
    "telegram": {"telegram", "tg", "телеграм", "t.me"},
    "google": {"google", "gads", "google_ads", "adwords"},
}
MACRO = re.compile(r"\{[^}]+\}|%7B|\[[A-Z_]+\]|\$\{")
EMPTY = {"", "none", "null", "undefined", "(not set)", "не определено", "-"}


def _find(cols: list[str], suffix: str) -> str | None:
    for c in cols:
        if c.lower().endswith(suffix.lower()):
            return c
    return None


def canon(v: str) -> str:
    s = re.sub(r"\s+", "", (v or "").strip().lower())
    for k, al in ALIASES.items():
        if s in al:
            return k
    return s


def analyze(cols: list[str], rows: list[dict]) -> dict:
    src = _find(cols, "UTMSource")
    med = _find(cols, "UTMMedium")
    camp = _find(cols, "UTMCampaign")
    vis = next((c for c in cols if c.endswith(":visits")), None)
    total = sum(num(r.get(vis)) or 0 for r in rows) if vis else 0

    variants: dict[str, dict[str, float]] = {}
    no_source = 0.0
    bad_medium: dict[str, float] = {}
    macros: dict[str, float] = {}
    for r in rows:
        v = num(r.get(vis)) or 0 if vis else 0
        s = str(r.get(src) or "") if src else ""
        if s.strip().lower() in EMPTY:
            no_source += v
        else:
            variants.setdefault(canon(s), {}).setdefault(s, 0)
            variants[canon(s)][s] += v
        if med:
            m = str(r.get(med) or "").strip()
            if m and m.lower() not in EMPTY and m.lower() not in STANDARD_MEDIUM:
                bad_medium[m] = bad_medium.get(m, 0) + v
        for c in (src, med, camp):
            if c and MACRO.search(str(r.get(c) or "")):
                key = f"{c.split(':')[-1]}={r.get(c)}"
                macros[key] = macros.get(key, 0) + v
    spelling = {k: dict(sorted(d.items(), key=lambda x: -x[1]))
                for k, d in variants.items() if len(d) > 1}
    findings = []
    if spelling:
        findings.append({"severity": "major", "title": "Один источник записан по-разному",
                         "evidence": spelling})
    if bad_medium:
        findings.append({"severity": "minor", "title": "Нестандартные utm_medium",
                         "evidence": dict(sorted(bad_medium.items(), key=lambda x: -x[1])[:20])})
    if macros:
        findings.append({"severity": "major", "title": "Не подставились макросы в метках",
                         "evidence": dict(sorted(macros.items(), key=lambda x: -x[1])[:20])})
    share_no = round(no_source / total, 4) if total else None
    return {"total_visits": total, "no_utm_source_visits": no_source,
            "no_utm_source_share": share_no, "spelling_variants": spelling,
            "nonstandard_medium": bad_medium, "unsubstituted_macros": macros,
            "findings": findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    a = ap.parse_args(argv)
    cols, rows, _ = load_table(a.input)
    json.dump(analyze(cols, rows), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
