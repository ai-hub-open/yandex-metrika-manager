# Рецепты отчётов

Префикс тулов опущен — ищи по суффиксу. Везде подставь `counter_id`, период (`date1`, `date2: "yesterday"`) и ID целей. Ответ сразу сохраняй в `raw/` и прогоняй через `scripts/metrika_table.py`. Поля из колонки «сверь» в `mcp-tools-map.md` — если API их не принял, бери указанную замену.

## Качество данных

**R1. Роботы**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate"], dimensions: ["ym:s:isRobot","ym:s:lastsignTrafficSource"], limit: 50 })
```
Замена: метрика `ym:s:robotPercentage` по `ym:s:lastsignTrafficSource`. Динамика всплесков — то же через `report_bytime`, `group: "day"`.

**R2. Каналы: объём и качество**
```
report({ metrics: ["ym:s:visits","ym:s:users","ym:s:bounceRate","ym:s:pageDepth","ym:s:avgVisitDurationSeconds","ym:s:goal<MACRO>reaches","ym:s:goal<MACRO>conversionRate"],
         dimensions: ["ym:s:lastsignTrafficSource"], accuracy: "full" })
```
Быстрый вариант — `preset: "sources_summary"`.

**R3. Домены входа**
```
report({ metrics: ["ym:s:visits"], dimensions: ["ym:s:startURLDomain"], limit: 50 })
```
Замена: `ym:s:startURL` с `limit: 200` и разбор доменов в скрипте.

**R4. Самопереходы и сайты-источники**
```
report({ metrics: ["ym:s:visits"], dimensions: ["ym:s:lastsignReferalSource"],
         filters: "ym:s:lastsignTrafficSource=='referral'", limit: 100 })
```

## Источники и разметка

**R5. UTM-разметка целиком**
```
report({ metrics: ["ym:s:visits","ym:s:goal<MACRO>reaches"],
         dimensions: ["ym:s:lastsignUTMSource","ym:s:lastsignUTMMedium","ym:s:lastsignUTMCampaign"],
         include_undefined: true, limit: 500 })
```
→ `python -m scripts.utm_hygiene --input raw/utm.json`. Быстрый вариант — `preset: "tags_u_t_m"`.

**R6. Реклама без меток**
```
report({ metrics: ["ym:s:visits"], dimensions: ["ym:s:lastsignSourceEngine","ym:s:lastsignUTMSource"],
         filters: "ym:s:lastsignTrafficSource=='ad'", include_undefined: true, limit: 100 })
```
Строки с пустым `utm_source` — неразмеченная реклама по системам.

**R7. Поисковые фразы (органика + реклама)**
```
report({ preset: "sources_search_phrases", limit: 100 })
```

## Директ

Логины — `chief_login` из `direct_clients_get`.

**R8. Клики → визиты → расход по кампаниям (неймспейс `ym:ad:`)**
```
report({ direct_client_logins: [...], currency: "RUB",
         metrics: ["ym:ad:clicks","ym:ad:visits","ym:ad:RUBAdCost"],
         dimensions: ["ym:ad:directOrder"], limit: 200 })
```
Потеря = `1 − visits / clicks`. Не принял поле → `preset: "sources_direct_summary"` с `direct_client_logins`.

**R9. Конверсии по кампаниям Директа (неймспейс `ym:s:`)**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate","ym:s:goal<MACRO>reaches","ym:s:goal<MACRO>conversionRate"],
         dimensions: ["ym:s:lastsignDirectClickOrder"],
         filters: "ym:s:lastsignTrafficSource=='ad'", limit: 200 })
```
Склейка R8+R9 по названию кампании → CPA по Метрике: `python -m scripts.metrika_table --input r9.json --join r8.json --join-key ym:s:lastsignDirectClickOrder --join-other-key ym:ad:directOrder --cost-col ym:ad:RUBAdCost --goal-col ym:s:goal<MACRO>reaches`.

**R10. Фразы Директа с поведением**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate","ym:s:goal<MACRO>reaches"],
         dimensions: ["ym:s:lastsignDirectClickOrder","ym:s:lastsignDirectPhraseOrCond"],
         filters: "ym:s:lastsignTrafficSource=='ad'", sort: ["-ym:s:visits"], limit: 300 })
```
Замена фразы: `ym:s:lastsignSearchPhrase`.

**R11. Поиск vs сети**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate","ym:s:goal<MACRO>conversionRate"],
         dimensions: ["ym:s:lastsignDirectPlatformType"], filters: "ym:s:lastsignTrafficSource=='ad'" })
```

## Поведение

**R12. Страницы входа**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate","ym:s:pageDepth","ym:s:goal<MACRO>conversionRate"],
         dimensions: ["ym:s:startURL"], sort: ["-ym:s:visits"], limit: 50 })
```
Раздробленные URL с параметрами → `ym:s:startURLPath` (сверь) или свернуть в скрипте.

**R13. Устройства**
```
report({ metrics: ["ym:s:visits","ym:s:bounceRate","ym:s:goal<MACRO>conversionRate"], dimensions: ["ym:s:deviceCategory"] })
```

**R14. Регионы**
```
report({ metrics: ["ym:s:visits","ym:s:goal<MACRO>conversionRate"], dimensions: ["ym:s:regionCity"], limit: 30 })
```

**R15. Новые vs вернувшиеся**
```
report({ metrics: ["ym:s:visits","ym:s:goal<MACRO>conversionRate"], dimensions: ["ym:s:isNewUser"] })
```
Замена: метрика `ym:s:percentNewVisitors` по каналам.

**R16. Воронка из целей** — одна строка, все шаги:
```
report({ metrics: ["ym:s:visits","ym:s:goal<STEP1>visits","ym:s:goal<STEP2>visits","ym:s:goal<STEP3>visits","ym:s:goal<MACRO>visits"] })
```
`goal<ID>visits` (визиты с достижением) — сверь; замена — `goal<ID>reaches`. Тот же запрос с `dimensions: ["ym:s:deviceCategory"]` или по каналам — где воронка рвётся сильнее. Составная цель (`step`) даёт шаги прямо в `goals_get`.

**R17. Час / день недели**
```
report({ metrics: ["ym:s:visits","ym:s:goal<MACRO>conversionRate"], dimensions: ["ym:s:hour"] })
```

## Динамика и сравнение

**R18. Тренд ключевых метрик**
```
report_bytime({ metrics: ["ym:s:visits","ym:s:goal<MACRO>reaches","ym:s:bounceRate"], group: "week", date1: "84daysAgo", date2: "yesterday" })
```

**R19. Период к периоду** — два одинаковых `report` с разными `date1/date2` → `metrika_table.py --input cur.json --compare prev.json --key <группировка>` → дельты и **вклад каждой строки в общее изменение**.

**R20. Проверка сегмента перед созданием** — тот же `filters`, что будет в `expression`:
```
report({ metrics: ["ym:s:visits","ym:s:users"], filters: "<expression>", date1: "30daysAgo", date2: "yesterday" })
```
Пользователей меньше ~1000 за 30 дней → для ретаргетинга Директа маловато, предупредить.
