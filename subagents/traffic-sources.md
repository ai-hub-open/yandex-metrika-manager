# Бриф субагента `traffic-sources` — Шаг 4 аудита

> **Это не отдельный скилл, а инструкция для форка.** Оркестратор `yandex-metrika-manager` передаёт тебе содержимое этого файла как задачу плюс аргументы.
>
> **Аргументы:** `$0` slug, `$1` counter_id, `$2` период `date1..date2`, `$3` ID макро-целей.

Ты — изолированный субагент Шага 4. Истории разговора у тебя нет. Собери картину каналов и разметки, сохрани сырьё на диск, верни наверх **сводку не длиннее 20 строк**.

## Read-only — жёстко

Вызывай только тулы, оканчивающиеся на `yandex_metrika_report`, `yandex_metrika_report_bytime`, `yandex_metrika_goals_get`, плюс Bash/Read/Write. **Никаких** `goals_add/update/delete`, `segments_add/delete` — даже с `dry_run`.

## Вход

Чего нет в аргументах — из `metrika/$0/_state.json` (`connector_prefix`, `unsupported_fields`). Пиши в `metrika/$0/audit/`.

## Методология (прочитай)

От корня скилла `yandex-metrika-manager`: `references/report-recipes.md` (R2, R5, R6, R7, R4), `references/audit-checklist.md` → «Разметка и источники», «Качество данных» (прямые заходы, самопереходы), `references/mcp-tools-map.md` → «Справочник», «Ошибки».

## Шаги

1. **Каналы (R2)** с `accuracy: "full"` → `raw/04_channels.json` → `python -m scripts.metrika_table --input raw/04_channels.json --min-visits 100 --goal-col ym:s:goal<MACRO>reaches > 04_channels.csv`. Квадрант «объём × качество» (`analysis-playbook.md` §3).
2. **UTM (R5)** → `raw/04_utm.json` → `python -m scripts.utm_hygiene --input raw/04_utm.json > 04_utm_hygiene.json`.
3. **Реклама без меток (R6)** → доля по системам.
4. **Сайты-источники (R4)** → самопереходы, платёжные шлюзы, мессенджеры, ушедшие в «ссылки».
5. **Поисковые фразы (R7)** — только топ-30, для контекста.
6. Поле не принято API → замена из `mcp-tools-map.md`, допиши поле в `_state.json` → `unsupported_fields`.

## Выход

- `04_sources.md` — таблица каналов, квадрант, разметка, проблемы с числами.
- `04_utm_hygiene.json` — вывод скрипта.
- `04_findings.json` — массив находок по схеме `report-template.md` (`area`: «Разметка и источники»).
- Наверх: сводка ≤20 строк — структура трафика (топ-5 каналов: доля, CR), находки 🔴/🟠 с одним числом-доказательством, что не удалось собрать.
