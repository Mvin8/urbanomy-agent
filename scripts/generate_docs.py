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
    return Settings(data_dir=ROOT / "data", output_dir=ROOT / "outputs/docs",
                    host="127.0.0.1", port=8080, public_url="http://localhost:8080",
                    token="", max_jobs=2, timeout_seconds=3600)


async def render_documents():
    settings = documentation_settings()
    service = UrbanomyService(settings)
    try:
        tools = await build_mcp(service).list_tools()
    finally:
        service.jobs.close()
    catalog = ["# MCP-инструменты\n",
               "Автогенерация: `python scripts/generate_docs.py`; проверка: `--check`.\n",
               "[Примеры и правила](tool_contract.md) · [Полные JSON-схемы](mcp_schemas.json)\n",
               "Транспорт: Streamable HTTP `/mcp` или stdio `python -m urbanomy_mcp`.\n",
               "Обязательные аргументы выделены **жирным**.\n"]
    schemas = {}
    for tool in tools:
        schema = tool.inputSchema
        required = schema.get("required", [])
        args = [f"**`{name}`**" if name in required else f"`{name}`"
                for name in schema.get("properties", {})]
        catalog.extend([f"## `{tool.name}`\n", (tool.description or "").split(". ")[0].rstrip(".") + ".\n",
                        "Аргументы: " + (", ".join(args) if args else "нет") + ".\n"])
        schemas[tool.name] = {"description": tool.description, "inputSchema": schema,
                              "outputSchema": tool.outputSchema}
    card = MessageToDict(build_card(settings))
    agent = """# A2A-агент

Автогенерация: `python scripts/generate_docs.py`; проверка: `--check`.

- Протокол: **A2A 1.0**, JSON-RPC `/a2a`, заголовок `A2A-Version: 1.0`.
- Карточка: `/.well-known/agent-card.json`.
- Операции: `estimate_land_value`, `optimize_district`.
- Долгие задачи: `GetTask`, `CancelTask`, поток `SendStreamingMessage`.
- Артефакты: сводка, JSON с результатами и GeoJSON.

[Запросы и статусы](tool_contract.md#подключение-по-a2a) · [Пример Agent Card](a2a_card.json)

JSON-пример использует `http://localhost:8080` без авторизации. Реальная карточка
учитывает `URBANOMY_PUBLIC_URL` и настройку Bearer token.
"""
    return {"mcp_tool_catalog.md": "\n".join(catalog), "a2a_agent_card.md": agent,
            "mcp_schemas.json": json.dumps(schemas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            "a2a_card.json": json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True) + "\n"}



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
