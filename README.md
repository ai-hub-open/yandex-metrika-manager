# yandex-metrika-manager

> Аудит, анализ и управление Яндекс Метрикой через MCP-коннектор Метрики. Три режима в одном скилле.

- **Аудит** (по умолчанию, read-only) — можно ли верить данным: паспорт счётчика, качество данных, цели, разметка, связка с Директом, поведение → HTML-отчёт.
- **Анализ** (read-only) — ответ на вопрос по данным или регулярный разбор (`pulse.md`), дерево разрезов «симптом → причина», A/B-гипотезы, ТЗ.
- **Управление** — цели и сегменты под гейтом: снимок → проект → `dry_run` → «ОК» → запись → журнал с откатом → проверка срабатывания.

Правка кампаний Директа — не здесь: `yandex-direct-audit`, `yandex-direct-manager`.

## Состав

| Путь | Зачем |
|---|---|
| `SKILL.md` | оркестратор: mode-gate, Шаги 0–7 аудита, анализ, управление |
| `subagents/` | брифы форков: `traffic-sources`, `direct-bridge`, `behavior-funnel` |
| `references/` | карта MCP, чек-лист с порогами, рецепты отчётов, плейбук анализа, дизайн целей, безопасность записи, шаблон отчёта |
| `scripts/` | `metrika_table`, `goals_health`, `utm_hygiene`, `ab_calc`, `changes_log`, `render_report` (только stdlib); `make_bundle` — сборка архива |
| `assets/findings_example.json` | образец `findings.json` |
| `tests/` | pytest без сети — обязательный гейт перед мержем |
| `evals/evals.json` | тест-кейсы скилла |
| `VERSION` | версия скилла — по ней он сообщает, что вышла новая |
| `.claude-plugin/plugin.json` | манифест плагина Claude Code (в архив не входит) |

## Что нужно

MCP Метрики (хостед на aihub, через click.ru или прямой OAuth). В click.ru должна быть подключена интеграция Метрики — иначе тулы отвечают «не подключена Яндекс Метрика».

## Установка

### Claude Code — плагином, с обновлениями

1. **Коннектор Метрики** — тот же адрес, что для Claude Desktop. ⚠️ Адрес с токеном равносилен паролю: не пересылать.

   ```
   claude mcp add --scope user --transport http yandex-metrika "<адрес коннектора Метрики>"
   ```

2. **Скилл** — в сессии Claude Code:

   ```
   /plugin marketplace add ai-hub-open/claude-plugins
   /plugin install yandex-metrika-manager@ai-hub-open
   ```

   Вызывается как `/yandex-metrika-manager:yandex-metrika-manager` или словами («проверь Метрику»).
   Автообновление: `/plugin` → **Marketplaces** → `ai-hub-open` → **Enable auto-update**; без него —
   `/plugin marketplace update ai-hub-open`.

Рабочая папка `metrika/` создаётся в текущей папке, а не внутри плагина: папка плагина при обновлении
заменяется целиком. Если раньше скилл лежал папкой в `~/.claude/skills/`, удалите её, иначе скилл
загрузится дважды.

### Claude Desktop и claude.ai

Скачайте `yandex-metrika-manager.zip` из [релизов](https://github.com/ai-hub-open/yandex-metrika-manager/releases/latest)
(или соберите: `python -m scripts.make_bundle`) и загрузите в Settings → Capabilities → Skills. В архив не
входят тесты, CI, манифест плагина, `.env` и рабочие папки.

## Тесты

```
python -m pytest -q
```

## Лицензия

[Apache-2.0](LICENSE).
