# A2A-агент

Автогенерация: `python scripts/generate_docs.py`. Проверка: `--check`.

- Протокол: **A2A 1.0**, JSON-RPC `/a2a`, заголовок `A2A-Version: 1.0`.
- Карточка: `/.well-known/agent-card.json`.
- Операции: `estimate_land_value`, `optimize_district`.
- Долгие задачи: `GetTask`, `CancelTask`, поток `SendStreamingMessage`.
- Артефакты: сводка, JSON с результатами и GeoJSON.

[Запросы и статусы](tool_contract.md#подключение-по-a2a) · [Пример Agent Card](a2a_card.json)

JSON-пример использует `http://localhost:8080` без авторизации. Реальная карточка
учитывает `URBANOMY_PUBLIC_URL` и настройку Bearer token.
