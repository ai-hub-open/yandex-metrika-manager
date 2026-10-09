#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_bundle.py — собирает yandex-metrika-manager.zip для загрузки в Claude Desktop / claude.ai
(Settings -> Capabilities -> Skills) и для релизов на GitHub.

Главное, ради чего скрипт существует: бандл раздаётся дальше, и в него НЕ должны
попасть ни секреты (.env), ни данные клиентов (metrika/), ни инструменты разработки
(tests/, CI, манифест плагина). Поэтому список исключений — по умолчанию, а не опция.

Использование:
    python -m scripts.make_bundle
    python -m scripts.make_bundle --output путь/к/bundle.zip
"""

import argparse
import fnmatch
import os
import sys
import zipfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SKILL_NAME = "yandex-metrika-manager"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Каталоги, которые не едут в бандл целиком.
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "metrika",         # рабочие папки — данные клиентов
    "tests",           # гейт перед мерджем, пользователю не нужен
    "dist",
    ".claude",
    ".github",         # CI репозитория
    ".claude-plugin",  # манифест плагина Claude Code
}

# Файлы по маскам. ".git" здесь тоже: в git worktree это файл, а не папка.
EXCLUDE_FILES = [
    ".git",
    ".env", ".env.*",
    "*.pyc", "*.pyo",
    "*.zip",
    ".gitignore",
    ".DS_Store",
    "pytest.ini",
    "CHANGELOG.md",
]

# Без этих файлов скилл нерабочий — проверяем перед упаковкой.
REQUIRED = [
    "SKILL.md",
    "VERSION",
    "LICENSE",
    "references/mcp-tools-map.md",
    "subagents/traffic-sources.md",
    "subagents/direct-bridge.md",
    "subagents/behavior-funnel.md",
    "scripts/render_report.py",
]


def excluded_file(name):
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_FILES)


def collect(skill_dir=SKILL_DIR):
    """Пути файлов бандла относительно корня скилла, в стабильном порядке."""
    found = []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for name in sorted(files):
            if excluded_file(name):
                continue
            rel = os.path.relpath(os.path.join(root, name), skill_dir).replace("\\", "/")
            found.append(rel)
    return found


def problems(rels):
    """Список причин не собирать бандл. Пустой — всё в порядке."""
    out = ["нет обязательного файла: {}".format(r) for r in REQUIRED if r not in rels]

    # Claude Desktop принимает ровно один SKILL.md на бандл: брифы субагентов
    # называются subagents/<имя>.md.
    skills = [r for r in rels if os.path.basename(r) == "SKILL.md"]
    if len(skills) != 1:
        out.append("SKILL.md должен быть ровно один, найдено {}: {}".format(len(skills), ", ".join(skills)))

    # Страховка от собственной ошибки в масках: секрет в бандле хуже, чем несобранный бандл.
    for r in rels:
        if os.path.basename(r).startswith(".env") or r.startswith(("metrika/", "tests/")):
            out.append("в бандл попало то, чего там быть не должно: {}".format(r))
    return out


def main():
    ap = argparse.ArgumentParser(description="Сборка zip-бандла скилла")
    ap.add_argument("--output", default=os.path.join(SKILL_DIR, SKILL_NAME + ".zip"),
                    help="путь к zip (по умолчанию {}.zip в корне скилла)".format(SKILL_NAME))
    args = ap.parse_args()

    rels = collect()
    errs = problems(rels)
    if errs:
        print("Бандл не собран:", file=sys.stderr)
        for e in errs:
            print("  - {}".format(e), file=sys.stderr)
        sys.exit(1)

    # Одна папка верхнего уровня с именем скилла — её загрузчик показывает как имя скилла.
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in rels:
            zf.write(os.path.join(SKILL_DIR, rel), arcname=SKILL_NAME + "/" + rel)

    size_kb = os.path.getsize(args.output) / 1024.0
    print("Бандл готов: {} ({:.0f} КБ, файлов: {})".format(args.output, size_kb, len(rels)))
    print("Загрузи zip в Claude Desktop: Settings -> Capabilities -> Skills.")


if __name__ == "__main__":
    main()
