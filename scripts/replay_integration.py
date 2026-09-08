"""Replay a saved demo request against a running HTTP MCP server."""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("estimate", "optimize", "optimize-llm"))
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/integration-replay")
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    request = json.loads((ROOT / f"examples/integration/{args.case}.request.json").read_text())
    token = os.getenv("URBANOMY_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    started = time.monotonic()
    async with streamablehttp_client(args.url.rstrip("/") + "/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, payload):
                response = await session.call_tool(name, payload)
                if response.isError:
                    raise RuntimeError(response.content)
                return response.structuredContent or json.loads(response.content[0].text)

            catalog = await call("list_scenarios", {})
            assert any(s["scenario_id"] == request["scenario_id"] for s in catalog["scenarios"])
            await call("get_optimization_options", {k: request[k] for k in ("scenario_id", "target_id")})
            tool = "estimate_land_value" if args.case == "estimate" else "start_district_optimization"
            job = await call(tool, request)
            while job["status"] == "working":
                if time.monotonic() - started > args.timeout:
                    await call("cancel_job", {"job_id": job["job_id"]})
                    raise TimeoutError("Demo timed out; cancellation requested")
                await asyncio.sleep(1)
                job = await call("get_job_status", {"job_id": job["job_id"]})
            if job["status"] != "completed":
                raise RuntimeError(job)
            response = await call("get_job_result", {"job_id": job["job_id"]})
            spatial = await call("get_job_geojson", {"job_id": job["job_id"]})
            args.output.mkdir(parents=True, exist_ok=True)
            for suffix, data in (("response.json", response), ("geojson", spatial),
                                 ("run.json", {"case": args.case, "wall_seconds": round(time.monotonic() - started, 3),
                                               "transport": "MCP Streamable HTTP", "request": request})):
                (args.output / f"{args.case}.{suffix}").write_text(
                    json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            print(response["result"]["summary"])
            print(f"PASS: {args.case}; results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
