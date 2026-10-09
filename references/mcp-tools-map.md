# Коннектор Метрики: тулы, параметры, справочник

## Подключение

Коннектор — хостед-MCP Метрики на шлюзе aihub (как у Директа и Wordstat). Имя коннектора задаёт пользователь (`metrikaCM`, `MetrikaClient`…), поэтому **тулы ищутся по суффиксу**, а не по префиксу: `…yandex_metrika_counters_get`, `…yandex_metrika_report` и т. д.

Режимы авторизации (по аналогии с коннектором Директа):
- **через click.ru** — токен click.ru; счётчики берутся из интеграций Метрики пользователя в click.ru, у каждого счётчика указан аккаунт. Если интеграции нет — тулы возвращают «У пользователя click.ru не подключена Яндекс Метрика» (проверено живьём) → подключить аккаунт Яндекса с Метрикой в интеграциях click.ru;
- **прямой OAuth-токен Яндекса** — аккаунт один, сам токен.

Параметр `account` (логин или ID интеграции из `accounts_get`) почти никогда не нужен — сервер сам находит аккаунт, которому доступен счётчик. Передавай его, только если один счётчик виден из нескольких аккаунтов с разным уровнем доступа и нужен конкретный (например, `edit` для записи).

## Тулы

### Read-only (все режимы)

| Суффикс | Что даёт | Ключевые параметры |
|---|---|---|
| `yandex_metrika_accounts_get` | аккаунты/интеграции подключения | — |
| `yandex_metrika_counters_get` | список счётчиков: номер, сайт, зеркала, статус, `permission` (own/edit/view), владелец, часовой пояс | `search` (домен/название/номер), `permission`, `with_goals`, `limit`, `status` |
| `yandex_metrika_counter_get` | один счётчик подробно: код, вебвизор, часовой пояс | `fields`: `goals`, `mirrors`, `grants`, `filters`, `operations`, `counter_flags` |
| `yandex_metrika_goals_get` | цели: ID, тип, условия, шаги, ценность | `stats_days` (1–365) → ещё `reaches` и `conversion_rate` по каждой цели; `include_deleted` |
| `yandex_metrika_segments_get` | сегменты: ID, имя, `expression`, статус | — |
| `yandex_metrika_direct_clients_get` | клиенты Директа, которых видит счётчик: ID, название, `chief_login` | — |
| `yandex_metrika_report` | таблица: группировки × метрики за период; `columns`, `rows`, `totals`, `total_rows`, признак семплирования | см. ниже |
| `yandex_metrika_report_bytime` | динамика: `intervals`, `series`, `totals` | + `group` (day/week/month/…), `top_keys` (≤30) |

### Пишущие (только режим Управление, только после гейта)

| Суффикс | Что делает | Класс | `dry_run` |
|---|---|---|---|
| `yandex_metrika_goals_add` | создать цель; начинает считать **сразу, без истории** | обратимая (можно удалить, но это необратимо уже для статистики) | есть |
| `yandex_metrika_goals_update` | изменить цель; **передавать цель целиком**, иначе пропущенные поля сбрасываются | обратимая (before в журнале) | есть |
| `yandex_metrika_goals_delete` | удалить цель; статистика перестаёт копиться, **кампании Директа теряют цель** | **необратимая** | есть |
| `yandex_metrika_segments_add` | создать сегмент (`expression` в синтаксисе `filters`; лимит 500 на счётчик) | обратимая | есть |
| `yandex_metrika_segments_delete` | удалить сегмент; **ретаргетинг Директа по нему перестаёт работать** | **необратимая** | есть |

По умолчанию `dry_run: false` — изменения применяются сразу. Поэтому в Управлении **первый вызов любой записи — всегда с `dry_run: true`**.

## Параметры отчётов

- `counter_id` — обязателен.
- `date1` / `date2` — `YYYY-MM-DD`, `today`, `yesterday`, `NdaysAgo`. Дефолт тула — последние 7 дней включая сегодня. **Для анализа бери полные дни**: `date2: "yesterday"` (сегодняшний неполный день занижает итоги и рисует ложное падение).
- `metrics` — до 20; `dimensions` — до 10.
- `filters` — `ym:s:lastsignTrafficSource=='ad' AND ym:s:deviceCategory=='mobile'`. Значения в одинарных кавычках. Операторы: `==`, `!=`, `=@` (содержит), `!@`, `=~` (регэксп), `!~`, `>`, `<`. Логика `AND`, `OR`, `NOT`, скобки.
- `preset` — шаблоны: `sources_summary`, `sources_search_phrases`, `sources_direct_summary`, `tags_u_t_m`, `traffic`, `conversion`. Явные `metrics`/`dimensions` перекрывают шаблон. Удобно для первого быстрого взгляда.
- `attribution` — `lastsign` (последний значимый, дефолт), `last`, `first`, `last_yandex_direct_click`, `cross_device_last_significant`.
- `accuracy` — `low`/`medium`/`high`/`full`. Ключевые цифры для отчёта — `full`.
- `limit` (≤1000, дефолт 100), `offset` (с 1), `sort` (`-` — по убыванию), `include_undefined`.
- `direct_client_logins` — нужны для любых `ym:ad:*` метрик (расходы Директа). Логины — `chief_login` из `direct_clients_get`.
- `currency` — валюта денежных метрик (`RUB`).

## Справочник группировок и метрик

**Подтверждены описанием тула** (используй смело):

- Группировки: `ym:s:lastsignTrafficSource`, `ym:s:lastsignSourceEngine`, `ym:s:lastsignUTMSource`, `ym:s:lastsignUTMCampaign`, `ym:s:lastsignDirectClickOrder` (кампания Директа), `ym:s:lastsignSearchPhrase`, `ym:s:startURL`, `ym:s:deviceCategory`, `ym:s:regionCity`, `ym:s:date`.
- Метрики: `ym:s:visits`, `ym:s:users`, `ym:s:pageviews`, `ym:s:bounceRate`, `ym:s:pageDepth`, `ym:s:avgVisitDurationSeconds`, `ym:s:anyGoalConversionRate`, `ym:s:goal<ID>reaches`, `ym:s:goal<ID>conversionRate`, `ym:ad:*` (с `direct_client_logins`).

**Из API Метрики, сверь первым вызовом** (если API ответит «unknown field» — убери поле и запиши в `_state.json` → `unsupported_fields`, не повторяй):

| Поле | Зачем |
|---|---|
| `ym:s:lastsignUTMMedium`, `ym:s:lastsignUTMContent`, `ym:s:lastsignUTMTerm` | разметка |
| `ym:s:lastsignReferalSource` | сайты-источники, самопереходы |
| `ym:s:lastsignDirectPlatformType`, `ym:s:lastsignDirectPhraseOrCond` | поиск/сети, фраза Директа |
| `ym:s:startURLDomain`, `ym:s:startURLPath` | домены и пути входа |
| `ym:s:isRobot` | роботы (значения `Yes`/`No`) |
| `ym:s:isNewUser` | новые/вернувшиеся |
| `ym:s:regionCountry`, `ym:s:hour`, `ym:s:dayOfWeek`, `ym:s:browser`, `ym:s:operatingSystemRoot` | срезы |
| `ym:s:robotPercentage`, `ym:s:percentNewVisitors`, `ym:s:goal<ID>visits` | метрики |
| `ym:ad:clicks`, `ym:ad:visits`, `ym:ad:RUBAdCost`, `ym:ad:RUBAdCostPerVisit` | Директ: клики, визиты, расход |
| `ym:ad:directOrder`, `ym:ad:directPhraseOrCond`, `ym:ad:directPlatformType` | группировки Директа для `ym:ad:*` |

**Правило неймспейсов:** в одном запросе не смешивай `ym:s:*` и `ym:ad:*` — для отчёта с расходами все группировки и метрики берутся из `ym:ad:`. Конверсии к расходу: `ym:ad:goal<ID>reaches` (сверь) или второй запрос `ym:s:` по `lastsignDirectClickOrder` и склейка по названию кампании в `metrika_table.py`.

### Значения `ym:s:lastsignTrafficSource`

`ad` (реклама), `organic` (поиск), `direct` (прямые заходы), `referral` (ссылки на сайтах), `internal` (внутренние переходы), `social`, `messenger`, `email`, `recommend` (рекомендательные системы), `saved` (сохранённые страницы). Точные идентификаторы сверь по ответу первого отчёта по этой группировке.

## Правила объёма

- Тяни только нужные поля; `limit` по задаче (топ-50 страниц, а не 1000).
- Длинный хвост режь фильтром по объёму: `filters: "ym:s:visits>10"` — сверь, что фильтр по метрике принят; иначе режь в `metrika_table.py --min-visits`.
- Динамика — `report_bytime` с `top_keys` ≤ 10, а не `report` по `ym:s:date` × группировка.
- Сырые ответы → `raw/<шаг>_<что>.json` сразу, в контекст — только итог.

## Ошибки и фолбеки

| Симптом | Что значит | Что делать |
|---|---|---|
| «не подключена Яндекс Метрика или интеграция не работает» | в click.ru нет интеграции Метрики / протухла | стоп; подключить в интеграциях click.ru или дать коннектор с OAuth |
| счётчик не находится по `search` | нет доступа у этого аккаунта | попросить номер счётчика; проверить `accounts_get`; выдать доступ аккаунту |
| `permission: view` | только просмотр | Аудит/Анализ — да, Управление — нет |
| ответ семплирован | Метрика считала по выборке | `accuracy: "full"` для ключевых цифр или пометить приближённость |
| unknown field / invalid metric | поле не поддерживается | убрать, записать в `unsupported_fields`, взять замену |
| пустые `ym:ad:*` | нет `direct_client_logins` или нет связи счётчика с Директом | `direct_clients_get`; пусто — Директ не связан (находка) |
| таймаут на тяжёлом отчёте | много строк/группировок | сузить период, убрать группировку, `limit` |
