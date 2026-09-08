# Карта кода Urbanomy

Краткий индекс для поиска реализации и проверок. Начните с
[README](../README.md) и [архитектуры](architecture.md).

| Задача | Реализация | Проверки |
|---|---|---|
| Изменить аргументы расчёта | `urbanomy_agent/schemas.py` | `tests/test_tool_contract.py` |
| Добавить MCP-инструмент | `urbanomy_mcp/tools.py` | `tests/test_mcp_tool_exposure.py` |
| Изменить A2A-контракт | `urbanomy_agent/a2a.py` | `tests/test_a2a_card.py`, `tests/test_a2a_tasks.py` |
| Изменить доступ к HTTP | `urbanomy_agent/server.py` | `tests/test_auth.py` |
| Изменить выполнение заданий | `urbanomy_agent/jobs.py` | `tests/test_runtime.py` |
| Настроить пути и окружение | `urbanomy_agent/settings.py`, `.env.example` | `tests/test_settings.py` |
| Добавить набор кварталов | `data/<scenario_id>/`, `urbanomy_agent/data.py` | `tests/test_data.py` |
| Изменить строгие ограничения | `urbanomy_agent/engine.py` | `tests/test_optimization.py` |
| Изменить модель/сценарии | `urbanomy/land_value/`, `urbanomy/investment/` | `tests/test_optimization.py` |
| Обновить каталог и карточку | `scripts/generate_docs.py` | `tests/test_tool_catalog_docs.py` |

## Маршруты чтения

- Подключение: [быстрый запуск](../RUN.md) → [развёртывание](deployment.md).
- Вызов инструмента: [контракт](tool_contract.md) → [каталог MCP](mcp_tool_catalog.md).
- Подключение агента: [Agent Card](a2a_agent_card.md) → раздел A2A в контракте.
- Изменение реализации: нужная строка таблицы → [команды проверок](../tests/README.md).

`examples/main.ipynb` — исследовательский пример, а не точка входа сервера.
`outputs/`, `.venv/` и кэши не являются исходным кодом.
Параметры модели и credentials поступают из окружения. В документацию и тестовые
снимки попадают только фиктивные значения.
