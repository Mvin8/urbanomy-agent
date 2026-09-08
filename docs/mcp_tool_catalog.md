# MCP-инструменты

Автогенерация: `python scripts/generate_docs.py`. Проверка: `--check`.

[Примеры и правила](tool_contract.md) · [Полные JSON-схемы](mcp_schemas.json)

Транспорт: Streamable HTTP `/mcp` или stdio `python -m urbanomy_mcp`.

Обязательные аргументы выделены **жирным**.

## `list_scenarios`

List prepared scenario directories under DATA_DIR.

Аргументы: нет.

## `list_blocks`

List block ids and baseline properties, in pages of up to 200.

Аргументы: **`scenario_id`**, `offset`, `limit`.

## `get_optimization_options`

Get target geometry, indicators, supported constraint names, units and physical limits.

Аргументы: **`scenario_id`**, **`target_id`**.

## `estimate_land_value`

Start land valuation with the pretrained CatBoost model (no LLM).

Аргументы: **`scenario_id`**, **`target_id`**, `project_id`.

## `start_district_optimization`

Start NSGA-II with hard bounds and an LLM strategy score.

Аргументы: **`scenario_id`**, **`target_id`**, **`strategy`**, `constraints`, `use_llm`, `pop_size`, `n_gen`, `seed`, `constraints_profile`, `project_id`.

## `get_job_status`

Get working/completed/failed/canceled state and evaluation progress.

Аргументы: **`job_id`**.

## `get_job_result`

Get completed valuation or Pareto scenarios, summary, effective constraints and provenance.

Аргументы: **`job_id`**.

## `get_job_geojson`

Get WGS84 GeoJSON: valuation for all blocks or alternatives for the selected block.

Аргументы: **`job_id`**.

## `cancel_job`

Stop the job's worker process.

Аргументы: **`job_id`**.
