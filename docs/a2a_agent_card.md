# Карточка A2A-агента

Генерируется из `urbanomy_agent/a2a.py`. Не редактировать руками.

Обновление: `python scripts/generate_docs.py`. Проверка без записи: `--check`.

[Подключение и запросы](tool_contract.md#a2a-и-codesynapse) · [Развёртывание](deployment.md)

Пример для `http://localhost:8080`, без авторизации. Реальная карточка доступна по `/.well-known/agent-card.json`: URL зависит от `URBANOMY_PUBLIC_URL`, а при заданном `URBANOMY_API_TOKEN` она дополнительно объявляет Bearer security scheme. Сам токен в карточку не попадает.

## Agent Card

```json
{
  "capabilities": {
    "extensions": [
      {
        "description": "Structured Urbanomy input; constraints_json supports Codesynapse scalar parameter extraction.",
        "params": {
          "additionalProperties": false,
          "properties": {
            "constraints_json": {
              "description": "For optimization: JSON object of explicit bounds, e.g. {\"l\":{\"min\":1,\"max\":8}}. Do not invent limits. Omitted variables stay fixed.",
              "type": "string"
            },
            "dataset_id": {
              "description": "Exact registered dataset id. Never infer it from a city name.",
              "type": "string"
            },
            "n_gen": {
              "maximum": 200.0,
              "minimum": 1.0,
              "type": "integer"
            },
            "operation": {
              "description": "Choose land valuation or district scenario optimization.",
              "enum": [
                "estimate_land_value",
                "optimize_district"
              ],
              "type": "string"
            },
            "pop_size": {
              "maximum": 100.0,
              "minimum": 4.0,
              "type": "integer"
            },
            "seed": {
              "minimum": 0.0,
              "type": "integer"
            },
            "strategy": {
              "description": "User's scenario evaluation strategy (soft preferences).",
              "type": "string"
            },
            "target_id": {
              "description": "Exact block id from the dataset, as a string. Never invent an id.",
              "type": "string"
            },
            "use_llm": {
              "description": "Default true. False explicitly disables strategy scoring.",
              "type": "boolean"
            }
          },
          "required": [
            "operation",
            "dataset_id",
            "target_id"
          ],
          "type": "object"
        },
        "required": true,
        "uri": "http://localhost:8080/extensions/urbanomy-input/v1"
      }
    ],
    "streaming": true
  },
  "defaultInputModes": [
    "text/plain",
    "application/json"
  ],
  "defaultOutputModes": [
    "text/plain",
    "application/json"
  ],
  "description": "Land valuation and constrained NSGA-II district optimization with LLM strategy scoring.",
  "name": "Urbanomy",
  "skills": [
    {
      "description": "Predict target and dataset land value from registered spatial data.",
      "id": "estimate_land_value",
      "name": "Оценка земли",
      "tags": [
        "land",
        "valuation"
      ]
    },
    {
      "description": "Evaluate constrained scenarios and return a Pareto front with economic metrics and optional LLM scores.",
      "id": "optimize_district",
      "name": "Оптимизация квартала",
      "tags": [
        "urban",
        "optimization",
        "strategy"
      ]
    }
  ],
  "supportedInterfaces": [
    {
      "protocolBinding": "JSONRPC",
      "protocolVersion": "1.0",
      "url": "http://localhost:8080/a2a"
    }
  ],
  "version": "0.1.0"
}
```

## Навыки

### `estimate_land_value` — Оценка земли

Predict target and dataset land value from registered spatial data.

### `optimize_district` — Оптимизация квартала

Evaluate constrained scenarios and return a Pareto front with economic metrics and optional LLM scores.

## Совместимость

Используется A2A **1.0**, SDK **1.1.1**. Для JSON-RPC нужен заголовок `A2A-Version: 1.0`. Проверки в `tests/test_codesynapse_contract.py` используют внешнюю схему Codesynapse через `A2A_CONTRACTS_DIR`; копия схемы в проекте не хранится.
