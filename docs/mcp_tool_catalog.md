# Каталог MCP-инструментов

Генерируется из `urbanomy_mcp/tools.py`. Не редактировать руками.

Обновление: `python scripts/generate_docs.py`. Проверка без записи: `--check`.

[Контракт и примеры вызовов](tool_contract.md) · [Индекс](README.md)

Опубликовано инструментов: **9**.

## `list_datasets`

List registered datasets. Remote callers cannot open arbitrary server paths.

Входная JSON Schema:

```json
{
  "properties": {},
  "title": "list_datasetsArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "list_datasetsDictOutput",
  "type": "object"
}
```

## `list_blocks`

List block ids and baseline properties, in pages of up to 200. Never invent a block id.

Входная JSON Schema:

```json
{
  "properties": {
    "dataset_id": {
      "title": "Dataset Id",
      "type": "string"
    },
    "limit": {
      "default": 50,
      "title": "Limit",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "title": "Offset",
      "type": "integer"
    }
  },
  "required": [
    "dataset_id"
  ],
  "title": "list_blocksArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "list_blocksDictOutput",
  "type": "object"
}
```

## `get_optimization_options`

Get target geometry, indicators, supported constraint names, units and physical limits.

Входная JSON Schema:

```json
{
  "properties": {
    "dataset_id": {
      "title": "Dataset Id",
      "type": "string"
    },
    "target_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "string"
        }
      ],
      "title": "Target Id"
    }
  },
  "required": [
    "dataset_id",
    "target_id"
  ],
  "title": "get_optimization_optionsArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "get_optimization_optionsDictOutput",
  "type": "object"
}
```

## `estimate_land_value`

Start land valuation with the pretrained CatBoost model (no LLM). Returns job_id; poll get_job_status.

Входная JSON Schema:

```json
{
  "properties": {
    "dataset_id": {
      "title": "Dataset Id",
      "type": "string"
    },
    "target_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "string"
        }
      ],
      "title": "Target Id"
    }
  },
  "required": [
    "dataset_id",
    "target_id"
  ],
  "title": "estimate_land_valueArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "estimate_land_valueDictOutput",
  "type": "object"
}
```

## `start_district_optimization`

Start NSGA-II with hard bounds and an LLM strategy score. Omitted variables stay at baseline.
        Get options first. strategy contains preferences; constraints contain hard numeric requirements.
        use_llm=false runs two economic objectives only. Returns job_id; use status/result/cancel tools.
        

Входная JSON Schema:

```json
{
  "$defs": {
    "Bounds": {
      "additionalProperties": false,
      "properties": {
        "max": {
          "title": "Max",
          "type": "number"
        },
        "min": {
          "title": "Min",
          "type": "number"
        },
        "type": {
          "const": "float",
          "default": "float",
          "title": "Type",
          "type": "string"
        }
      },
      "required": [
        "min",
        "max"
      ],
      "title": "Bounds",
      "type": "object"
    }
  },
  "properties": {
    "constraints": {
      "additionalProperties": {
        "$ref": "#/$defs/Bounds"
      },
      "title": "Constraints",
      "type": "object"
    },
    "dataset_id": {
      "title": "Dataset Id",
      "type": "string"
    },
    "n_gen": {
      "default": 20,
      "title": "N Gen",
      "type": "integer"
    },
    "pop_size": {
      "default": 20,
      "title": "Pop Size",
      "type": "integer"
    },
    "seed": {
      "default": 42,
      "title": "Seed",
      "type": "integer"
    },
    "strategy": {
      "title": "Strategy",
      "type": "string"
    },
    "target_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "string"
        }
      ],
      "title": "Target Id"
    },
    "use_llm": {
      "default": true,
      "title": "Use Llm",
      "type": "boolean"
    }
  },
  "required": [
    "dataset_id",
    "target_id",
    "constraints",
    "strategy"
  ],
  "title": "start_district_optimizationArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "start_district_optimizationDictOutput",
  "type": "object"
}
```

## `get_job_status`

Get working/completed/failed/canceled state and evaluation progress. Poll every few seconds.

Входная JSON Schema:

```json
{
  "properties": {
    "job_id": {
      "title": "Job Id",
      "type": "string"
    }
  },
  "required": [
    "job_id"
  ],
  "title": "get_job_statusArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "get_job_statusDictOutput",
  "type": "object"
}
```

## `get_job_result`

Get completed valuation or Pareto scenarios, summary, effective constraints and provenance.

Входная JSON Schema:

```json
{
  "properties": {
    "job_id": {
      "title": "Job Id",
      "type": "string"
    }
  },
  "required": [
    "job_id"
  ],
  "title": "get_job_resultArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "get_job_resultDictOutput",
  "type": "object"
}
```

## `get_job_geojson`

Get WGS84 GeoJSON: valuation for all blocks or alternatives for the selected block.

Входная JSON Schema:

```json
{
  "properties": {
    "job_id": {
      "title": "Job Id",
      "type": "string"
    }
  },
  "required": [
    "job_id"
  ],
  "title": "get_job_geojsonArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "get_job_geojsonDictOutput",
  "type": "object"
}
```

## `cancel_job`

Stop the job's worker process. Canceling one job does not stop another.

Входная JSON Schema:

```json
{
  "properties": {
    "job_id": {
      "title": "Job Id",
      "type": "string"
    }
  },
  "required": [
    "job_id"
  ],
  "title": "cancel_jobArguments",
  "type": "object"
}
```

Выходная JSON Schema:

```json
{
  "additionalProperties": true,
  "title": "cancel_jobDictOutput",
  "type": "object"
}
```
