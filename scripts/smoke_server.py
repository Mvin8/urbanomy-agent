"""Exercise a running MCP + A2A server. --compute uses the real model, never an LLM."""
import argparse
import asyncio
import json
import os
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--compute", action="store_true")
    parser.add_argument("--dataset", default="baseline")
    parser.add_argument("--target", default="86")
    args = parser.parse_args()
    token = os.getenv("URBANOMY_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(base_url=args.url, headers=headers, timeout=180) as http:
        (await http.get("/health")).raise_for_status()
        card = (await http.get("/.well-known/agent-card.json")).json()
        assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0"
        async with streamablehttp_client(args.url.rstrip("/") + "/mcp", headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 9

                async def call(name, payload):
                    result = await session.call_tool(name, payload)
                    assert not result.isError, result
                    return result.structuredContent or json.loads(result.content[0].text)

                print("MCP tools:", ", ".join(tool.name for tool in tools.tools))
                print("Datasets:", await call("list_datasets", {}))
                if args.compute:
                    options = await call("get_optimization_options", dict(dataset_id=args.dataset, target_id=args.target))
                    print("Selected block:", options["target_id"])
                    job = await call("estimate_land_value", dict(dataset_id=args.dataset, target_id=args.target))
                    deadline = time.monotonic() + 180
                    while job["status"] == "working" and time.monotonic() < deadline:
                        await asyncio.sleep(1)
                        job = await call("get_job_status", {"job_id": job["job_id"]})
                    assert job["status"] == "completed", job
                    result = await call("get_job_result", {"job_id": job["job_id"]})
                    print("MCP valuation:", result["result"]["land_value"])
                    spatial = await call("get_job_geojson", {"job_id": job["job_id"]})
                    assert spatial["type"] == "FeatureCollection"

        payload = {"operation": "optimize_district", "dataset_id": args.dataset, "target_id": args.target,
                   "constraints": {"l": {"min": 1, "max": 3}}, "strategy": "Economic baseline; LLM disabled.",
                   "use_llm": False, "pop_size": 4, "n_gen": 1}
        if not args.compute:
            payload = {"operation": "invalid"}
        response = await http.post("/a2a", headers={"A2A-Version": "1.0"}, json={
            "jsonrpc": "2.0", "id": "smoke", "method": "SendMessage", "params": {
                "message": {"messageId": "smoke", "contextId": "smoke", "role": "ROLE_USER", "parts": [{"data": payload}]},
                "configuration": {"returnImmediately": False},
            }})
        response.raise_for_status()
        body = response.json()
        assert "error" not in body, body
        task = body["result"]["task"]
        assert task["status"]["state"] == ("TASK_STATE_COMPLETED" if args.compute else "TASK_STATE_FAILED"), task
        print("A2A:", task["status"]["state"])
        if args.compute:
            print(task["artifacts"][0]["parts"][0]["text"])
    print("PASS")


if __name__ == "__main__":
    asyncio.run(main())
