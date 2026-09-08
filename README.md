# urbanomy-agent

`urbanomy-agent` предоставляет два интерфейса для оценки стоимости земли и оптимизации
застройки квартала на основе библиотеки `urbanomy`:

- **MCP-сервер** (`python -m urbanomy_mcp`) — stdio, 9 инструментов для выбора данных,
  запуска расчётов и управления заданиями. Также доступен через Streamable HTTP `/mcp`.
- **A2A-агент** (`python -m urbanomy_agent`) — HTTP, 2 skill-а:
  `estimate_land_value` и `optimize_district`. Тот же процесс обслуживает HTTP MCP.

MCP предназначен для вызова инструментов из LLM-клиентов. A2A — для интеграции
в мультиагентные системы и HTTP-клиенты. Оценка земли и оптимизация с `use_llm=false`
работают без LLM; при `use_llm=true` требуется настроенный провайдер.

Главный навигационный индекс: [docs/WIKI-LLM.md](docs/WIKI-LLM.md).

## Концепция

Система подбирает параметры застройки на основе подготовленных геоданных:

1. **Оценка земли:** обученная модель CatBoost прогнозирует стоимость квартала
   с учётом его характеристик и окружения.
2. **Поиск вариантов:** NSGA-II ищет компромиссы между приростом стоимости земли
   всего сценария и NPV инвестора для выбранного квартала.
3. **Числовые ограничения:** границы параметров и производных показателей
   проверяются до оценки кандидата с помощью LLM.
4. **Текстовая стратегия:** опциональная LLM-оценка `llm_score` добавляет цель
   соответствия слабоформализуемым предпочтениям пользователя.
5. **Результат:** допустимые варианты Парето, экономические показатели,
   текстовая сводка и GeoJSON для отображения на карте.

Оба интерфейса используют `UrbanomyService` и запускают расчёты в отдельных
рабочих процессах. MCP-клиент отслеживает задание по `job_id`, A2A-клиент —
через задачи протокола и поток обновлений.

Данные выбираются по `scenario_id` из подготовленных папок `DATA_DIR/<scenario_id>/`.
Каждая содержит GeoJSON кварталов и модель `.cbm`; необязательный `scenario.json`
задаёт параметры подготовки. В репозиторий включён сценарий `baseline`.
`target_id` выбирает квартал, `project_id` служит только меткой проекта.
Требования к файлам — в [описании данных](docs/data.md).

## Quickstart

### Локальный запуск (без Docker)

Нужны Python 3.11–3.13 и данные из `data/baseline/`. Команды для macOS/Linux
выполняются из корня репозитория:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Создать .env, если его ещё нет
[ -f .env ] || cp .env.example .env
```

Для оценки стратегии заполните в `.env` значения `OPENAI_API_KEY`,
`URBANOMY_LLM_MODEL` и при необходимости `OPENAI_BASE_URL`.
Для расчётов без LLM эти настройки не требуются.

```bash
# MCP через stdio — процесс запускает MCP-клиент
python -m urbanomy_mcp

# HTTP-сервер с A2A и MCP — отдельный способ запуска
python -m urbanomy_agent
```

| Интерфейс | Адрес / команда |
|---|---|
| MCP Streamable HTTP | `http://localhost:8080/mcp` |
| A2A JSON-RPC | `http://localhost:8080/a2a` |
| Agent Card | `http://localhost:8080/.well-known/agent-card.json` |
| Проверка доступности | `http://localhost:8080/health` |
| MCP stdio | Python из `.venv`, аргументы `-m urbanomy_mcp`, рабочая директория проекта |

При заданном `URBANOMY_API_TOKEN` HTTP-вызовы MCP/A2A требуют заголовок
`Authorization: Bearer <token>`. A2A использует заголовок `A2A-Version: 1.0`.

### Docker

Подготовьте `.env` и папки сценариев, затем:

```bash
docker compose build
docker compose up -d
# A2A: http://localhost:8080/a2a
# MCP: http://localhost:8080/mcp
```

Compose запускает один сервис `urbanomy`. Каталог `./data` монтируется только
для чтения, результаты сохраняются в том `urbanomy-results`. Данные не входят в образ.

Подробнее — [RUN.md](RUN.md) и [docs/deployment.md](docs/deployment.md).

## Каталог инструментов и контракт

- **MCP:** [docs/mcp_tool_catalog.md](docs/mcp_tool_catalog.md) — 9 инструментов;
  полные схемы аргументов и ответов в [docs/mcp_schemas.json](docs/mcp_schemas.json).
- **A2A:** [docs/a2a_agent_card.md](docs/a2a_agent_card.md) — операции, задачи
  и артефакты; пример карточки в [docs/a2a_card.json](docs/a2a_card.json).
- **Контракт:** [docs/tool_contract.md](docs/tool_contract.md) — запросы,
  ограничения, статусы, ошибки и формат результатов.

Каталог, схемы и карточка генерируются из публичных интерфейсов командой
`python scripts/generate_docs.py`; проверка актуальности — с флагом `--check`.

## Структура репозитория

```text
urbanomy-agent/
├── README.md
├── RUN.md                      # краткая инструкция запуска
├── pyproject.toml              # зависимости, extras dev / notebook, CLI
├── .env.example                # настройки сервера и LLM
├── Dockerfile
├── compose.yaml                # общий HTTP-сервис MCP + A2A
├── urbanomy/                   # расчётная библиотека
│   ├── land_value/             # CatBoost, изменение параметров, NSGA-II
│   └── investment/             # инвестиционные метрики и NPV
├── urbanomy_agent/             # общее ядро сервиса и A2A
│   ├── server.py               # HTTP-приложение, маршруты, авторизация
│   ├── a2a.py                  # Agent Card и выполнение A2A-задач
│   ├── service.py              # общий вход для MCP и A2A
│   ├── schemas.py              # модели и валидация запросов
│   ├── data.py                 # сценарии, загрузка данных и модели
│   ├── engine.py               # расчёты и проверка ограничений
│   ├── constraint_profiles.py  # профили числовых ограничений
│   ├── jobs.py                 # рабочие процессы, статусы, отмена
│   ├── llm.py                  # подключение модели оценки стратегии
│   └── settings.py             # окружение и пути
├── urbanomy_mcp/               # MCP-сервер и определения инструментов
├── data/baseline/              # стандартный сценарий: GeoJSON, .cbm, metadata
├── examples/main.ipynb         # исследовательский пример
├── scripts/                    # генерация документации и smoke-проверка
├── tests/                      # проверки расчётов, контрактов и транспорта
└── docs/                       # архитектура, данные, контракты, развёртывание
```

## Контракт инструмента

Перед расчётом выберите сценарий и квартал через MCP:

| Шаг | Инструмент | Аргументы |
|---|---|---|
| 1 | `list_scenarios` | `{}` |
| 2 | `list_blocks` | `{"scenario_id":"baseline"}` |
| 3 | `estimate_land_value` | `{"scenario_id":"baseline","target_id":86}` |
| 4 | `get_job_status` | `{"job_id":"<полученный ID>"}` |
| 5 | `get_job_result` | Тот же `job_id`, после `completed` |

Для другого сценария используйте его ID и ID квартала из `list_blocks`.
Это MCP-вызовы, а не отдельные HTTP-маршруты.

Для оптимизации сначала вызовите `get_optimization_options(scenario_id, target_id)`:
он возвращает исходные показатели, единицы и допустимые параметры.
Пример аргументов `start_district_optimization`:

```json
{
  "scenario_id": "baseline",
  "target_id": 86,
  "constraints_profile": "test",
  "constraints": {"l": {"min": 3, "max": 6}},
  "strategy": "Предпочитать смешанное жилое и деловое использование",
  "use_llm": false,
  "pop_size": 20,
  "n_gen": 30,
  "seed": 42
}
```

Профиль `test` задаёт пятно застройки от 1 м² до 10% площади квартала,
этажность 1–10, MXI 0,1–1 и семь долей землепользования 0–1 с суммой 1.
Явные `constraints` заменяют границы профиля по параметрам; в примере этажность
сужена до 3–6. Без профиля неуказанные параметры фиксируются на исходных значениях.
Нужен профиль или непустой `constraints`.

При `use_llm=false` стратегия сохраняется, но не влияет на поиск.
Для оценки стратегии настройте LLM и передайте `use_llm: true`.
В A2A соответствующие операции — `estimate_land_value` и `optimize_district`;
пример JSON-RPC приведён в [контракте](docs/tool_contract.md#подключение-по-a2a).

## Финальный ответ

### Жизненный цикл одного вызова

```text
MCP-инструмент / A2A SendMessage
└── UrbanomyService: проверка запроса и сценария
    └── JobManager: запуск рабочего процесса
        ├── загрузка кварталов и CatBoost
        ├── оценка земли / оптимизация NSGA-II с ограничениями
        └── сохранение результата и GeoJSON
            ├── MCP: get_job_status → get_job_result / get_job_geojson
            └── A2A: GetTask или поток SendStreamingMessage → артефакты
```

MCP возвращает `job_id` сразу. Статусы задания: `working`, `completed`, `failed`,
`canceled`. Для долгих расчётов проверяйте состояние каждые 10–15 секунд;
доступны прошедшее время и число обработанных кандидатов. Отмена — `cancel_job`.
В A2A используются `GetTask` и `CancelTask`.

### Что получает клиент

| Результат | Основные поля / содержание |
|---|---|
| Оценка земли | `land_value`, `land_value_per_sqm`, `dataset_land_value_total`, `currency` |
| Оптимизация | `scenarios`, `baseline_land_value_total`, `effective_constraints`, `constraints_profile`, `evaluations` |
| Вариант Парето | `params_repaired`, `land_value_after`, `land_value_gain`, `investor_npv`, при LLM — `llm_score` |
| Сводка и происхождение данных | `summary`, `provenance` |
| Геоданные | GeoJSON в WGS84: оценки кварталов или варианты выбранного квартала |

MCP возвращает расчётные поля внутри `result` ответа `get_job_result`, а GeoJSON —
через `get_job_geojson`. A2A передаёт сводку, JSON и GeoJSON в артефактах задачи.

Прирост стоимости земли относится ко всему сценарию, NPV — к выбранному кварталу.
Варианты Парето показывают компромиссы между целями; окончательный выбор делает
пользователь. Границы квартала сохраняются, контуры отдельных зданий не проектируются.

## Индексация WIKI-LLM

| Индекс | Назначение |
|---|---|
| [docs/WIKI-LLM.md](docs/WIKI-LLM.md) | Карта кода, точки изменения и связанные проверки |
| [docs/README.md](docs/README.md) | Навигация по документации |
| [tests/README.md](tests/README.md) | Наборы тестов и команды запуска |

## Документация

| Документ | О чём |
|---|---|
| [Интеграционное демо](docs/integration.md) | Эталонные запросы, результаты, локальные ресурсы и промпты |
| [docs/architecture.md](docs/architecture.md) | Общее ядро, MCP/A2A и выполнение расчётов |
| [docs/tool_contract.md](docs/tool_contract.md) | Запросы, ограничения, результаты и ошибки |
| [docs/mcp_tool_catalog.md](docs/mcp_tool_catalog.md) | Автогенерируемый каталог MCP-инструментов |
| [docs/a2a_agent_card.md](docs/a2a_agent_card.md) | Карточка A2A и операции агента |
| [docs/data.md](docs/data.md) | Папки сценариев, признаки, геометрии и модель |
| [docs/deployment.md](docs/deployment.md) | Локальный запуск, Docker, окружение и диагностика |
| [RUN.md](RUN.md) | Краткая инструкция запуска и проверки |
| [examples/main.ipynb](examples/main.ipynb) | Исследовательский пример оптимизации |

## Статус

Реализованы 9 MCP-инструментов, 2 A2A-операции, Bearer-авторизация HTTP,
фоновые задания с отменой и Docker-запуск. Сервис работает с подготовленными
сценариями; поиск участков по адресу, сбор исходных данных и создание генплана
не входят в его функции.

По умолчанию доступны 2 параллельных расчёта с лимитом 60 минут на задание.
Очереди нет. Перезапуск прерывает активные задания, а доступ к старым заданиям
через API не восстанавливается; сохранённые файлы остаются в каталоге результатов.

Проверки из активированного окружения:

```bash
python -m pytest -q
python scripts/generate_docs.py --check

# При запущенном HTTP-сервере: настоящие данные, без LLM
python scripts/smoke_server.py --compute
```

Smoke-проверка выполняет оценку земли через MCP и короткую оптимизацию через A2A;
при успехе выводит `PASS`. Маршрут `/health` проверяет только доступность сервера.
