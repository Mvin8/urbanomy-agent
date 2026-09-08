# Быстрый запуск

Из корня репозитория, Python 3.11–3.13:

```bash
python -m pip install -e '.[dev]'
python -m urbanomy_agent
```

Параметры — в [.env.example](.env.example). Дополните существующий `.env`.
Для LLM-оптимизации нужны ключ провайдера и `URBANOMY_LLM_MODEL`.
Расчёт стоимости земли и оптимизация с `use_llm=false` работают без LLM.

| Подключение | Адрес |
|---|---|
| MCP Streamable HTTP | `http://localhost:8080/mcp` |
| A2A JSON-RPC | `http://localhost:8080/a2a` |
| Agent Card | `http://localhost:8080/.well-known/agent-card.json` |
| Health | `http://localhost:8080/health` |

Для MCP через stdio: `python -m urbanomy_mcp`.
Для Docker: `docker compose up --build -d` (нужны `.env` и `data/`).
Данные читаются из `DATA_DIR/<scenario_id>/`; стандартный сценарий — `data/baseline/`.
[Структура и требования к данным](docs/data.md).

В другом терминале:

```bash
python scripts/smoke_server.py --compute
```

Проверяется реальная оценка через MCP и короткая оптимизация через A2A для
`baseline`, квартал `86`. LLM отключён. Для другого набора используйте
`--scenario` и `--target`; при авторизации передайте `URBANOMY_API_TOKEN` через окружение.

- [Настройки, Docker и ограничения](docs/deployment.md)
- [Данные, constraints, strategy/prompt и A2A](docs/tool_contract.md)
- [Автоматические тесты](tests/README.md)
- [Вся документация](docs/README.md)
