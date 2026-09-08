# Запросы и результаты

[Данные](data.md) · [Каталог MCP](mcp_tool_catalog.md) · [Карточка A2A](a2a_agent_card.md)

## Выбор сценария

1. `list_scenarios` — получить имена подготовленных папок.
2. `list_blocks(scenario_id)` — выбрать `target_id`. Доступны `offset` и `limit` (1–200).
3. `get_optimization_options(scenario_id, target_id)` — получить геометрию, исходные
   показатели, единицы и допустимые параметры.

ID не выводятся из адреса или названия города. `project_id` в расчётных запросах
необязателен и служит только меткой проекта.

## Оценка земли

`estimate_land_value`:

```json
{"scenario_id":"baseline","target_id":86}
```

Результат: `land_value` (рубли за квартал), `land_value_per_sqm` (рубли за м²),
`dataset_land_value_total` (сумма по всему сценарию), `currency`, `summary`, `provenance`.
GeoJSON содержит оценки всех кварталов.

## Оптимизация

`start_district_optimization`:

```json
{
  "scenario_id": "baseline",
  "target_id": 86,
  "constraints_profile": "test",
  "constraints": {"l": {"min": 3, "max": 6}},
  "strategy": "Предпочитать смешанное жилое и деловое использование",
  "use_llm": false,
  "pop_size": 20,
  "n_gen": 20,
  "seed": 42
}
```

`constraints` задаёт жёсткие границы вида `{"min":число,"max":число}`.
Поле `type` можно опустить, поддерживается только `float`.

- Свободные параметры: `footprint_area`, средняя этажность `l` и семь долей
  землепользования из [описания данных](data.md).
- Производные ограничения: `mxi`, `fsi`, `gsi`, `build_floor_area`, `living_area`,
  `non_living_area`, `population`. Проверяются после пересчёта кандидата, до LLM.
- Доли должны давать сумму 1. `min == max` фиксирует параметр. Пятно застройки
  должно быть положительным и не больше 80% `site_area`. Средняя этажность `l >= 1`.

Профиль `test` хранится в [constraint_profiles.py](../urbanomy_agent/constraint_profiles.py):
пятно 1 м²–10% `site_area`, этажность 1–10, MXI 0,1–1, все семь долей 0–1.
Это широкий тестовый диапазон, допускающий полную смену назначения территории.
При слишком малой площади квартала переопределите границы пятна.

Явный `constraints` заменяет границы профиля целиком по соответствующему параметру.
Без профиля неуказанные параметры остаются исходными. Доли предварительно нормализуются.
Нужен профиль или непустой `constraints`, и хотя бы один свободный параметр с ненулевым диапазоном.

`strategy` обязательна. При `use_llm=true` LLM оценивает соответствие стратегии по
параметрам кандидата, приросту стоимости земли и NPV. Ответ ожидается как JSON
`{"score":0.0}` с числом от 0 до 1. Некорректный ответ приводит к ошибке расчёта.
Текст стратегии не заменяет числовые границы. При `use_llm=false` он не влияет на поиск.
`pop_size`: 4–100, `n_gen`: 1–200. Значения по умолчанию — 20 и 20.

Результат содержит `scenarios`, `constraints_profile`, `effective_constraints`,
`baseline_land_value_total`, `evaluations`, `summary`, `provenance`.
В каждом варианте: `params_repaired`, `land_value_after`, `land_value_gain`,
`investor_npv`, а при LLM — `llm_score`.
Стоимость земли и её прирост относятся ко всему сценарию, а NPV — к выбранному кварталу.
Варианты Парето показывают компромиссы, единственный лучший вариант автоматически не выбирается.
Границы квартала одинаковы для всех вариантов. Контуры зданий не проектируются.

## Долгие расчёты

Старт возвращает `job_id`. `get_job_status(job_id)` возвращает `status`,
`elapsed_seconds` и, когда доступно, `progress.evaluations` — число обработанных кандидатов.
Статусы: `working`, `completed`, `failed`, `canceled`. Процента и прогноза времени нет.
Проверяйте состояние раз в несколько секунд. Для долгих задач достаточно 10–15 секунд.

При `completed` вызовите `get_job_result` и `get_job_geojson`. `cancel_job` останавливает
расчёт. По умолчанию лимит — 60 минут. Перезапуск сервера прерывает активные задания.
Ошибка возвращается с причиной. Основные коды: `SCENARIO_NOT_MATERIALIZED`,
`SERVER_BUSY`, `TIMEOUT`, `WORKER_EXITED`, `CALCULATION_FAILED`.
`NO_FEASIBLE_SOLUTION` в сообщении означает, что допустимый вариант не найден в бюджете поиска.

## Подключение по A2A

Endpoint `/a2a`, заголовок `A2A-Version: 1.0`. При включённой авторизации также нужен
`Authorization: Bearer <token>`. Пример JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "m-1",
      "role": "ROLE_USER",
      "parts": [{"data": {
        "operation": "estimate_land_value",
        "scenario_id": "baseline",
        "target_id": "86"
      }}]
    },
    "configuration": {"returnImmediately": true}
  }
}
```

Для оптимизации используйте `operation: "optimize_district"` и поля из MCP-примера.
A2A также принимает `prompt` вместо `strategy` и строку `constraints_json` вместо
объекта `constraints`. Одновременно оба варианта одного поля запрещены.

`SendMessage` возвращает `result.task`. `GetTask` с `{"id":"<task-id>"}` получает
состояние и артефакты. `CancelTask` отменяет задачу. Если задан `tenant`, передавайте его
во всех вызовах. `returnImmediately=false` ждёт завершения. Настройте таймаут клиента.
`SendStreamingMessage` передаёт обновления через SSE.
Артефакты содержат текстовую сводку, JSON и GeoJSON.
