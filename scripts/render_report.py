#!/usr/bin/env python3
"""render_report.py — findings.json → самодостаточный HTML-отчёт аудита Метрики.

Без внешних пакетов и сети. Печать в PDF — из браузера (Ctrl+P).

  python -m scripts.render_report --input metrika/<slug>/audit/findings.json [--output out.html]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys

SEV = {
    "critical": ("🔴", "Срочно", "#c62828"),
    "major": ("🟠", "Важно", "#ef6c00"),
    "minor": ("🟡", "Гигиена", "#f9a825"),
    "info": ("⚪", "К сведению", "#757575"),
}
SEV_ORDER = ["critical", "major", "minor", "info"]
AREAS = ["Паспорт", "Качество данных", "Цели", "Разметка и источники", "Директ", "Поведение и воронки"]
TRUST = {"высокая": "#2e7d32", "средняя": "#ef6c00", "низкая": "#c62828"}

CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#6b6b70;--card:#f6f6f8;--line:#e3e3e8}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececf0;--muted:#a0a0a8;--card:#1f1f23;--line:#2e2e34}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 48px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
.muted{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.tile{background:var(--card);border-radius:10px;padding:12px 14px}.tile b{display:block;font-size:22px}.tile span{color:var(--muted);font-size:13px}
.card{background:var(--card);border-radius:10px;padding:14px 16px;margin:10px 0;border-left:4px solid var(--c);break-inside:avoid}
.card h3{margin:0 0 6px;font-size:16px}.kv{margin:4px 0}.kv i{font-style:normal;color:var(--muted)}
pre{white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:8px;font-size:13px}
ol.top li{margin:4px 0}ul.lim li{margin:3px 0}footer{margin-top:36px;color:var(--muted);font-size:13px}
@media print{body{font-size:12px}main{max-width:none}.card{page-break-inside:avoid}}
"""


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def fmt_num(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v < 1:
        return f"{v*100:.1f}%".replace(".", ",")
    try:
        return f"{int(round(float(v))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return esc(v)


def card(f: dict) -> str:
    icon, label, color = SEV.get(f.get("severity", "info"), SEV["info"])
    rows = [
        ("Что видим", f.get("evidence")),
        ("Что сделать", f.get("recommendation")),
        ("Где", f.get("where")),
        ("Кто", f.get("owner")),
        ("Как проверить самому", f.get("how_to_verify")),
        ("Ожидаемый эффект", f.get("expected_effect")),
        ("Уверенность", f.get("confidence")),
    ]
    body = "".join(f'<div class="kv"><i>{k}:</i> {esc(v)}</div>' for k, v in rows if v)
    ready = f.get("ready_to_use")
    if ready:
        body += f"<pre>{esc(ready)}</pre>"
    return (f'<div class="card" style="--c:{color}"><h3>{icon} {esc(f.get("title"))} '
            f'<span class="muted">· {label}</span></h3>{body}</div>')


def render(data: dict) -> str:
    meta = data.get("meta", {})
    s = meta.get("summary", {})
    findings = data.get("findings", [])
    findings_sorted = sorted(findings, key=lambda f: SEV_ORDER.index(f.get("severity", "info"))
                             if f.get("severity", "info") in SEV_ORDER else 9)
    trust = s.get("data_trust")
    tiles = [
        ("Визиты", fmt_num(s.get("visits"))),
        (f"Достижения: {esc(s.get('macro_goal') or 'макро-цель')}", fmt_num(s.get("macro_reaches"))),
        ("Конверсия в макро-цель", fmt_num(s.get("macro_cr"))),
        ("Доля роботов", fmt_num(s.get("robots_share"))),
    ]
    tiles_html = "".join(f'<div class="tile"><span>{k}</span><b>{v}</b></div>' for k, v in tiles)
    if trust:
        tiles_html += (f'<div class="tile"><span>Доверие к данным</span>'
                       f'<b style="color:{TRUST.get(trust, "inherit")}">{esc(trust)}</b></div>')
    counts = {k: sum(1 for f in findings if f.get("severity") == k) for k in SEV_ORDER}
    counts_html = " · ".join(f"{SEV[k][0]} {SEV[k][1]}: {counts[k]}" for k in SEV_ORDER if counts[k])

    top = findings_sorted[:5]
    top_html = "".join(f"<li>{SEV.get(f.get('severity','info'), SEV['info'])[0]} <b>{esc(f.get('title'))}</b>"
                       f" — {esc(f.get('recommendation'))}</li>" for f in top)

    areas = AREAS + sorted({f.get("area") for f in findings if f.get("area") not in AREAS and f.get("area")})
    sections = ""
    for a in areas:
        items = [f for f in findings_sorted if f.get("area") == a]
        if items:
            sections += f"<h2>{esc(a)}</h2>" + "".join(card(f) for f in items)

    hyp = data.get("hypotheses") or []
    hyp_html = ""
    if hyp:
        hyp_html = "<h2>Гипотезы для A/B-тестов</h2>"
        for h in hyp:
            hyp_html += ('<div class="card" style="--c:#1565c0">'
                         f'<h3>🧪 {esc(h.get("hypothesis"))}</h3>'
                         f'<div class="kv"><i>Наблюдение:</i> {esc(h.get("observation"))}</div>'
                         f'<div class="kv"><i>Метрика:</i> {esc(h.get("metric"))}</div>'
                         f'<div class="kv"><i>Правило решения:</i> {esc(h.get("decision_rule"))}</div>'
                         f'<div class="kv"><i>Длительность:</i> {esc(h.get("duration"))}</div></div>')

    lim = meta.get("limitations") or []
    lim_html = ("<h2>Чего не смогли проверить</h2><ul class='lim'>" +
                "".join(f"<li>{esc(x)}</li>" for x in lim) + "</ul>") if lim else ""

    title = f"Аудит Метрики — {meta.get('site') or meta.get('slug') or ''}"
    period = esc(meta.get("period"))
    cmp_ = f" · сравнение с {esc(meta.get('compared_to'))}" if meta.get("compared_to") else ""
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head>
<body><main>
<h1>{esc(title)}</h1>
<div class="muted">Счётчик {esc(meta.get('counter_id'))} · период {period}{cmp_}</div>
<div class="tiles">{tiles_html}</div>
<div class="muted">{counts_html}</div>
<h2>Главное</h2><ol class="top">{top_html or '<li>Существенных проблем не найдено</li>'}</ol>
{sections}{hyp_html}{lim_html}
<footer>Отчёт подготовлен в режиме аудита: в счётчике ничего не менялось. Все действия выполняет команда вручную
или в режиме управления после отдельного согласования.</footer>
</main></body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    a = ap.parse_args(argv)
    with open(a.input, encoding="utf-8") as fh:
        data = json.load(fh)
    out = a.output or os.path.join(os.path.dirname(os.path.abspath(a.input)),
                                   f"АУДИТ_МЕТРИКИ_{data.get('meta', {}).get('slug', 'report')}.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(data))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
