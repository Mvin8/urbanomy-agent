# Эталонные примеры Urbanomy

Полная инструкция: [docs/integration.md](../../docs/integration.md).
[Проверка поведения агентов](agent-evals.md) отделена от системных промптов.
Для демонстрации передайте агенту текст задачи и содержимое нужного `*.request.json`.
Передача одного пути к файлу не подразумевает, что агент сможет его прочитать.

- `*.request.json` — аргументы MCP-инструмента.
- `*.a2a.json` — те же аргументы внутри A2A SendMessage. ReturnImmediately=true.
- `estimate.response.json`, `optimize.response.json` — реальные ответы HTTP MCP.
- `estimate.geojson`, `optimize.geojson` — реальные геоданные этих ответов.
- `*.run.json` — длительность HTTP-прогона и точный запрос.
- `benchmark.json` — девять локальных замеров расчётного сервиса без LLM.

Повторный запуск записывает новые файлы в outputs, сохраняя приложенный эталон:

```bash
python scripts/replay_integration.py estimate
python scripts/replay_integration.py optimize
```

Команды выполняются из корня проекта при запущенном сервере. LLM-вариант подготовлен
в `optimize-llm.request.json` и `optimize-llm.a2a.json`, но не проверен реальным вызовом.
Файлы ответов и benchmark содержат наблюдения одного окружения, а не гарантии времени
и точного совпадения результатов. Сохранённые job_id не действуют на новом сервере.
