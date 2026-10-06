#!/usr/bin/env python3
"""ab_calc.py — размер выборки и длительность A/B-теста конверсии (две доли).

  --base-cr        базовая конверсия (0.02 = 2%)
  --mde            минимальный детектируемый эффект, относительный (0.15 = +15%)
  --daily-visitors визитов в день, попадающих в тест (всего, на все варианты)
  --variants       число вариантов, по умолчанию 2
  --alpha/--power  0.05 / 0.8 по умолчанию (двусторонний тест)

Пример:
  python -m scripts.ab_calc --base-cr 0.012 --mde 0.15 --daily-visitors 280
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from statistics import NormalDist


def sample_size(base_cr: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
    if not (0 < base_cr < 1) or mde <= 0:
        raise ValueError("base_cr в (0,1), mde > 0")
    p1 = base_cr
    p2 = base_cr * (1 + mde)
    if p2 >= 1:
        raise ValueError("base_cr × (1+mde) должно быть меньше 1")
    z_a = NormalDist().inv_cdf(1 - alpha / 2)
    z_b = NormalDist().inv_cdf(power)
    p_bar = (p1 + p2) / 2
    n = (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return math.ceil(n)


def plan(base_cr, mde, daily_visitors, variants=2, alpha=0.05, power=0.8) -> dict:
    n = sample_size(base_cr, mde, alpha, power)
    days = math.ceil(n * variants / daily_visitors) if daily_visitors else None
    weeks = math.ceil(days / 7) if days else None
    verdict = "ok"
    if days and days > 56:
        verdict = "too_long"
    elif days and days < 7:
        verdict = "run_full_week"
    return {"per_variant": n, "total": n * variants, "days": days,
            "days_rounded_to_weeks": weeks * 7 if weeks else None,
            "expected_conversions_per_variant": round(n * base_cr, 1), "verdict": verdict,
            "note": {"ok": "Нормальная длительность; держать полными неделями.",
                     "too_long": "Дольше 8 недель — трафика мало: увеличить MDE, тестировать ближе к верху воронки или до/после с оговорками.",
                     "run_full_week": "Хватит меньше недели, но держать минимум 7 дней из-за недельной сезонности."}[verdict]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-cr", type=float, required=True)
    ap.add_argument("--mde", type=float, required=True)
    ap.add_argument("--daily-visitors", type=float, required=True)
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    a = ap.parse_args(argv)
    json.dump(plan(a.base_cr, a.mde, a.daily_visitors, a.variants, a.alpha, a.power),
              sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
