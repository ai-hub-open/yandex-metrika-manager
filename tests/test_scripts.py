import csv
import io
import json
import os
import subprocess
import sys

import pytest

from conftest import FIX, ROOT
from scripts import ab_calc, goals_health, metrika_table, utm_hygiene, render_report
from scripts._io import load_json, load_table


def f(name):
    return os.path.join(FIX, name)


def run(mod, *args):
    out = subprocess.run([sys.executable, "-m", f"scripts.{mod}", *args], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    return out.stdout, out.stderr


# --- _io ---------------------------------------------------------------
def test_load_table_unwraps_success_data():
    cols, rows, meta = load_table(f("channels_cur.json"))
    assert cols[0] == "ym:s:lastsignTrafficSource"
    assert rows[0]["ym:s:visits"] == 5000
    assert meta["sampled"] is False


def test_load_table_raw_api_format(tmp_path):
    p = tmp_path / "raw.json"
    p.write_text(json.dumps({"query": {"dimensions": ["ym:s:deviceCategory"], "metrics": ["ym:s:visits"]},
                             "data": [{"dimensions": [{"name": "desktop"}], "metrics": [10]}]}))
    cols, rows, _ = load_table(str(p))
    assert rows == [{"ym:s:deviceCategory": "desktop", "ym:s:visits": 10}]


# --- metrika_table -----------------------------------------------------
def _csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_enrich_share_and_cr():
    out, _ = run("metrika_table", "--input", f("channels_cur.json"), "--goal-col", "ym:s:goal123reaches")
    rows = {r["ym:s:lastsignTrafficSource"]: r for r in _csv(out)}
    assert float(rows["ad"]["cr"]) == pytest.approx(0.02)
    assert float(rows["organic"]["share"]) == pytest.approx(3000 / 9540, abs=1e-4)


def test_min_visits_aggregates_tail():
    out, _ = run("metrika_table", "--input", f("channels_cur.json"), "--min-visits", "100")
    rows = _csv(out)
    assert len(rows) == 4
    assert rows[-1]["ym:s:lastsignTrafficSource"].startswith("прочее (1")


def test_compare_contribution():
    out, _ = run("metrika_table", "--input", f("channels_cur.json"), "--compare", f("channels_prev.json"),
                 "--metric", "ym:s:goal123reaches", "--format", "json")
    rows = json.loads(out)
    top = rows[0]
    assert top["ym:s:lastsignTrafficSource"] == "ad"
    assert top["delta"] == -60
    # общее изменение 200-257 = -57 → вклад ad = 60/57
    assert top["share_of_total_delta"] == pytest.approx(60 / 57, abs=1e-3)


def test_join_cpa_and_unmatched_warning():
    out, err = run("metrika_table", "--input", f("direct_conv.json"), "--join", f("direct_ad.json"),
                   "--join-key", "ym:s:lastsignDirectClickOrder", "--join-other-key", "ym:ad:directOrder",
                   "--cost-col", "ym:ad:RUBAdCost", "--goal-col", "ym:s:goal123reaches")
    rows = {r["ym:s:lastsignDirectClickOrder"]: r for r in _csv(out)}
    assert float(rows["Поиск-Бренд"]["cpa"]) == 600.0   # склейка нечувствительна к регистру/пробелам
    assert float(rows["РСЯ-Охват"]["cpa"]) == 8400.0
    assert "Старая РК" in err


# --- goals_health ------------------------------------------------------
def test_goals_classification():
    goals = goals_health._goals(load_json(f("goals.json")))
    res = goals_health.classify(goals, visits=41200, macro_ids={2}, direct_ids={1})
    by = {g["id"]: g for g in res["goals"]}
    assert by[1]["status"] == "noisy" and by[1]["severity"] == "critical"
    assert "soft_goal_in_direct" in by[1]["flags"]
    assert by[2]["status"] == "ok" and "no_value" in by[2]["flags"]
    assert by[3]["status"] == "dead" and "bad_name" in by[3]["flags"]
    assert by[5]["status"] == "low_data"
    assert "generic_url_condition" in by[6]["flags"]
    assert [3, 4] in res["summary"]["duplicates"]
    assert res["summary"]["has_macro"] is True


def test_goals_cli():
    out, _ = run("goals_health", "--input", f("goals.json"), "--visits", "41200", "--macro-ids", "2")
    assert json.loads(out)["summary"]["by_status"]["dead"] == 2


# --- utm_hygiene -------------------------------------------------------
def test_utm_hygiene():
    cols, rows, _ = load_table(f("utm.json"))
    res = utm_hygiene.analyze(cols, rows)
    assert set(res["spelling_variants"]["yandex"]) == {"yandex", "Yandex", "ya"}
    assert "CPC-search" in res["nonstandard_medium"]
    assert any("{campaign_id}" in k for k in res["unsubstituted_macros"])
    assert res["no_utm_source_share"] == pytest.approx(3000 / 16740, abs=1e-4)


# --- ab_calc -----------------------------------------------------------
def test_ab_sample_size_known_value():
    # p=10%, +20% → классическое значение ≈ 3 840 на вариант
    n = ab_calc.sample_size(0.10, 0.20)
    assert 3700 < n < 4000


def test_ab_plan_too_long():
    p = ab_calc.plan(0.01, 0.10, daily_visitors=200)
    assert p["verdict"] == "too_long"


def test_ab_invalid():
    with pytest.raises(ValueError):
        ab_calc.sample_size(0.9, 0.5)


# --- changes_log -------------------------------------------------------
def test_changes_log_roundtrip(tmp_path):
    ws = str(tmp_path / "metrika" / "acme")
    run("changes_log", "record", "--workspace", ws, "--change", "2026-10-05", "--object-type", "goal",
        "--object-id", "3", "--field", "name", "--tool", "goals_update", "--class", "reversible",
        "--before", '{"name":"Цель 3"}', "--after", '{"name":"[OFF] Цель 3"}', "--status", "applied")
    run("changes_log", "record", "--workspace", ws, "--change", "2026-10-05", "--object-type", "goal",
        "--object-id", "4", "--field", "whole", "--tool", "goals_delete", "--class", "irreversible",
        "--before", '{"id":4}', "--status", "applied")
    out, _ = run("changes_log", "rollback-plan", "--workspace", ws, "--change", "2026-10-05")
    plan = json.loads(out.split("\n\n")[0])
    assert plan["restore"][0]["set_back_to"] == {"name": "Цель 3"}
    assert plan["cannot_auto_rollback"][0]["object_id"] == "4"


# --- render_report -----------------------------------------------------
def test_render_example(tmp_path):
    out_path = tmp_path / "r.html"
    run("render_report", "--input", os.path.join(ROOT, "assets", "findings_example.json"), "--output", str(out_path))
    h = out_path.read_text(encoding="utf-8")
    assert "Аудит Метрики — acme.ru" in h
    assert h.index("Директ учится на шумной цели") < h.index("теряет 31%")
    assert "ym:s:" not in h
    assert "Гипотезы для A/B" in h and "ничего не менялось" in h
