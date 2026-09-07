"""Generate the MCP catalog and A2A card from the actual public interfaces."""
import argparse
import asyncio
import json
from pathlib import Path

from google.protobuf.json_format import MessageToDict

from urbanomy_agent.a2a import build_card
from urbanomy_agent.service import UrbanomyService
from urbanomy_agent.settings import Settings
from urbanomy_mcp.server import build_mcp

ROOT = Path(__file__).resolve().parents[1]


def documentation_settings():
    """Deterministic public example, independent of local URLs and credentials."""
    return Settings(datasets_file=ROOT / "data/datasets.json", output_dir=ROOT / "outputs/docs",
                    host="127.0.0.1", port=8080, public_url="http://localhost:8080",
                    token="", max_jobs=2, timeout_seconds=3600)


def json_block(value):
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n```\n"


async def render_documents():
    settings = documentation_settings()
    service = UrbanomyService(settings)
    try:
        tools = await build_mcp(service).list_tools()
    finally:
        service.jobs.close()
    catalog = ["# Каталог MCP-инструментов\n",
               "Генерируется из `urbanomy_mcp/tools.py`. Не редактировать руками.\n",
               "Обновление: `python scripts/generate_docs.py`. Проверка без записи: `--check`.\n",
               "[Контракт и примеры вызовов](tool_contract.md) · [Индекс](README.md)\n",
               f"Опубликовано инструментов: **{len(tools)}**.\n"]
    for tool in tools:
        catalog.extend([f"## `{tool.name}`\n", (tool.description or "") + "\n",
                        "Входная JSON Schema:\n", json_block(tool.inputSchema),
                        "Выходная JSON Schema:\n", json_block(tool.outputSchema)])
    card = MessageToDict(build_card(settings))
    agent = ["# Карточка A2A-агента\n",
             "Генерируется из `urbanomy_agent/a2a.py`. Не редактировать руками.\n",
             "Обновление: `python scripts/generate_docs.py`. Проверка без записи: `--check`.\n",
             "[Подключение и запросы](tool_contract.md#a2a-и-codesynapse) · [Развёртывание](deployment.md)\n",
             "Пример для `http://localhost:8080`, без авторизации. Реальная карточка доступна по "
             "`/.well-known/agent-card.json`: URL зависит от `URBANOMY_PUBLIC_URL`, а при заданном "
             "`URBANOMY_API_TOKEN` она дополнительно объявляет Bearer security scheme. Сам токен в карточку не попадает.\n",
             "## Agent Card\n", json_block(card), "## Навыки\n"]
    for skill in card["skills"]:
        agent.extend([f"### `{skill['id']}` — {skill['name']}\n", skill["description"] + "\n"])
    agent.append("## Совместимость\n\nИспользуется A2A **1.0**, SDK **1.1.1**. Для JSON-RPC нужен заголовок "
                 "`A2A-Version: 1.0`. Проверки в `tests/test_codesynapse_contract.py` используют внешнюю "
                 "схему Codesynapse через `A2A_CONTRACTS_DIR`; копия схемы в проекте не хранится.\n")
    return {"mcp_tool_catalog.md": "\n".join(catalog), "a2a_agent_card.md": "\n".join(agent)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on outdated docs without modifying any files")
    args = parser.parse_args()
    outdated = []
    for filename, content in asyncio.run(render_documents()).items():
        path = ROOT / "docs" / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                outdated.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"Generated {path.relative_to(ROOT)}")
    if outdated:
        parser.exit(1, "Outdated documentation: " + ", ".join(outdated) + "\nRun python scripts/generate_docs.py\n")
    if args.check:
        print("Generated documentation is up to date.")


if __name__ == "__main__":
    main()
