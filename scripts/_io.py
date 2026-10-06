"""Общие загрузчики ответов MCP Метрики (стандартная библиотека)."""
from __future__ import annotations

import json
from typing import Any


def unwrap(obj: Any) -> Any:
    """Снимает обёртки {"success":..., "data": {...}} и {"result": ...}."""
    while isinstance(obj, dict) and len(obj) <= 4 and "query" not in obj:
        for k in ("data", "result"):
            if k in obj and isinstance(obj[k], (dict, list)):
                obj = obj[k]
                break
        else:
            break
    return obj


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return unwrap(json.loads(text))


def _col_name(c: Any) -> str:
    if isinstance(c, dict):
        return str(c.get("name") or c.get("id") or c.get("title"))
    return str(c)


def _cell(v: Any) -> Any:
    if isinstance(v, dict):
        for k in ("name", "value", "id"):
            if k in v:
                return v[k]
    return v


def load_table(path: str) -> tuple[list[str], list[dict], dict]:
    """Ответ yandex_metrika_report → (columns, rows-as-dicts, meta).

    Терпим к формам: rows как списки или словари; columns как строки или {name}.
    Также понимает «сырой» ответ API Метрики (query.dimensions/metrics + data[].dimensions/metrics).
    """
    obj = load_json(path)
    meta: dict = {}
    if isinstance(obj, dict):
        meta = {k: obj.get(k) for k in ("totals", "total_rows", "sampled", "sampleable") if k in obj}
        if "columns" in obj and "rows" in obj:
            cols = [_col_name(c) for c in obj["columns"]]
            rows = []
            for r in obj["rows"]:
                if isinstance(r, dict):
                    rows.append({c: _cell(r.get(c)) for c in cols})
                else:
                    rows.append({c: _cell(v) for c, v in zip(cols, r)})
            return cols, rows, meta
        if "query" in obj and "data" in obj:  # сырой формат API
            q = obj["query"]
            cols = list(q.get("dimensions", [])) + list(q.get("metrics", []))
            rows = []
            for d in obj["data"]:
                vals = [_cell(x) for x in d.get("dimensions", [])] + list(d.get("metrics", []))
                rows.append(dict(zip(cols, vals)))
            return cols, rows, meta
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        cols = list(obj[0].keys())
        return cols, obj, meta
    raise ValueError(f"не распознан формат отчёта в {path}")


def num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_metric(col: str) -> bool:
    return ":goal" in col or any(col.endswith(s) for s in (
        "visits", "users", "pageviews", "bounceRate", "pageDepth", "Seconds",
        "ConversionRate", "conversionRate", "reaches", "clicks", "Cost", "CostPerVisit",
        "Percentage", "percentNewVisitors"))
