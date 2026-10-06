#!/usr/bin/env python3
"""metrika_table.py — ответ yandex_metrika_report → CSV/JSON с производными.

Возможности:
  * производные: share (доля визитов), cr (цель/визиты), cpa (расход/цель);
  * фильтр по объёму: --min-visits (строки ниже уходят в агрегат «прочее»);
  * сравнение периодов: --compare prev.json → delta, delta_pct и вклад строки
    в общее изменение (share_of_total_delta) по главной метрике;
  * склейка с отчётом ym:ad:* (расход Директа): --join ad.json --join-key <колонка>.

Примеры:
  python -m scripts.metrika_table --input raw/04_channels.json --min-visits 100 \
      --goal-col ym:s:goal123reaches
  python -m scripts.metrika_table --input cur.json --compare prev.json --metric ym:s:goal123reaches
  python -m scripts.metrika_table --input conv.json --join ad.json --join-key ym:s:lastsignDirectClickOrder \
      --cost-col ym:ad:RUBAdCost --goal-col ym:s:goal123reaches
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

from scripts._io import is_metric, load_table, num


def _norm_key(v) -> str:
    return " ".join(str(v or "").strip().lower().split())


def pick_visits_col(cols: list[str]) -> str | None:
    for c in cols:
        if c.endswith(":visits") and ":goal" not in c:
            return c
    return None


def dim_cols(cols: list[str]) -> list[str]:
    return [c for c in cols if not is_metric(c)]


def enrich(rows: list[dict], visits_col: str | None, goal_col: str | None,
           cost_col: str | None) -> list[dict]:
    total_visits = sum(num(r.get(visits_col)) or 0 for r in rows) if visits_col else 0
    for r in rows:
        v = num(r.get(visits_col)) if visits_col else None
        g = num(r.get(goal_col)) if goal_col else None
        cost = num(r.get(cost_col)) if cost_col else None
        if visits_col and total_visits:
            r["share"] = round((v or 0) / total_visits, 4)
        if goal_col and v:
            r["cr"] = round((g or 0) / v, 4)
        if cost_col and goal_col:
            r["cpa"] = round(cost / g, 2) if (cost is not None and g) else None
    return rows


def apply_min_visits(rows: list[dict], visits_col: str, min_visits: float,
                     dims: list[str]) -> list[dict]:
    keep, rest = [], []
    for r in rows:
        (keep if (num(r.get(visits_col)) or 0) >= min_visits else rest).append(r)
    if rest:
        agg: dict = {d: "" for d in dims}
        if dims:
            agg[dims[0]] = f"прочее ({len(rest)} строк ниже {int(min_visits)} визитов)"
        for c in rest[0]:
            if c in dims:
                continue
            vals = [num(x.get(c)) for x in rest]
            # суммируем только аддитивные метрики; доли/средние не суммируются
            if c.endswith(("visits", "users", "pageviews", "reaches", "clicks", "Cost")):
                agg[c] = sum(v for v in vals if v is not None)
        keep.append(agg)
    return keep


def join_rows(rows: list[dict], other: list[dict], key: str, other_key: str | None) -> tuple[list[dict], list[str]]:
    other_key = other_key or key
    idx = {_norm_key(o.get(other_key)): o for o in other}
    unmatched = []
    for r in rows:
        o = idx.pop(_norm_key(r.get(key)), None)
        if o is None:
            continue
        for c, v in o.items():
            if c != other_key and c not in r:
                r[c] = v
    unmatched = [str(o.get(other_key)) for o in idx.values()]
    return rows, unmatched


def compare(cur: list[dict], prev: list[dict], keys: list[str], metric: str) -> list[dict]:
    def k(r):
        return tuple(_norm_key(r.get(x)) for x in keys)

    pidx = {k(r): r for r in prev}
    seen = set()
    out = []
    total_delta = sum(num(r.get(metric)) or 0 for r in cur) - sum(num(r.get(metric)) or 0 for r in prev)
    for r in cur:
        p = pidx.get(k(r), {})
        seen.add(k(r))
        out.append(_cmp_row(r, p, keys, metric, total_delta))
    for kk, p in pidx.items():
        if kk not in seen:
            out.append(_cmp_row({x: p.get(x) for x in keys}, p, keys, metric, total_delta))
    out.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return out


def _cmp_row(r, p, keys, metric, total_delta):
    c = num(r.get(metric)) or 0
    pv = num(p.get(metric)) or 0
    d = c - pv
    row = {x: r.get(x) for x in keys}
    row.update({"current": c, "previous": pv, "delta": round(d, 4),
                "delta_pct": round(d / pv, 4) if pv else None,
                "share_of_total_delta": round(d / total_delta, 4) if total_delta else None})
    return row


def write(rows: list[dict], fmt: str, out) -> None:
    if fmt == "json":
        json.dump(rows, out, ensure_ascii=False, indent=2)
        out.write("\n")
        return
    cols: list[str] = []
    for r in rows:
        for c in r:
            if c not in cols:
                cols.append(c)
    w = csv.DictWriter(out, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--visits-col")
    ap.add_argument("--goal-col")
    ap.add_argument("--cost-col")
    ap.add_argument("--min-visits", type=float, default=0)
    ap.add_argument("--compare", help="отчёт за прошлый период той же формы")
    ap.add_argument("--metric", help="главная метрика для сравнения (по умолчанию визиты)")
    ap.add_argument("--key", action="append", help="колонка-ключ (можно несколько); по умолчанию все группировки")
    ap.add_argument("--join", help="второй отчёт (обычно ym:ad:*) для склейки")
    ap.add_argument("--join-key")
    ap.add_argument("--join-other-key", help="имя ключа во втором отчёте, если отличается")
    ap.add_argument("--format", choices=["csv", "json"], default="csv")
    a = ap.parse_args(argv)

    cols, rows, meta = load_table(a.input)
    if meta.get("sampled"):
        print("⚠️  отчёт семплирован — для ключевых цифр повторите с accuracy=full", file=sys.stderr)
    dims = dim_cols(cols)
    visits_col = a.visits_col or pick_visits_col(cols)

    if a.join:
        if not a.join_key:
            ap.error("--join требует --join-key")
        _, other, _ = load_table(a.join)
        rows, unmatched = join_rows(rows, other, a.join_key, a.join_other_key)
        if unmatched:
            print(f"⚠️  не склеились строки второго отчёта ({len(unmatched)}): "
                  + "; ".join(unmatched[:10]), file=sys.stderr)

    if a.compare:
        _, prev, _ = load_table(a.compare)
        metric = a.metric or visits_col
        if not metric:
            ap.error("укажите --metric")
        write(compare(rows, prev, a.key or dims, metric), a.format, sys.stdout)
        return 0

    rows = enrich(rows, visits_col, a.goal_col, a.cost_col)
    if a.min_visits and visits_col:
        rows = apply_min_visits(rows, visits_col, a.min_visits, dims)
    write(rows, a.format, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
