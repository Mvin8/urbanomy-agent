import asyncio
from fastapi.testclient import TestClient
from urbanomy_agent.server import build_app
from urbanomy_agent.jobs import JobManager
from urbanomy_agent.service import UrbanomyService
from urbanomy_mcp.server import build_mcp
from tests.helpers import result_worker


def test_mcp_catalog_and_invocation(settings):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    mcp = build_mcp(service)
    async def check():
        tools = await mcp.list_tools()
        assert len(tools) == 9
        tool = next(t for t in tools if t.name == "start_district_optimization")
        assert {"scenario_id", "target_id", "strategy"} <= set(tool.inputSchema["required"])
        assert "constraints" not in tool.inputSchema["required"]
        profile_result = await mcp.call_tool("start_district_optimization", {"scenario_id": "test", "target_id": 86, "strategy": "Test", "constraints_profile": "test", "use_llm": False})
        assert "job_id" in str(profile_result)
        result = await mcp.call_tool("estimate_land_value", {"scenario_id": "test", "target_id": 86})
        assert "job_id" in str(result)
    try:
        asyncio.run(check())
    finally:
        service.jobs.close()



def test_mcp_http_requests_do_not_close_job_manager(settings):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    with TestClient(build_app(settings, service)) as client:
        def call(method, params):
            response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                                   json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            assert response.status_code == 200, response.text
            return response.json()["result"]
        call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
        result = call("tools/call", {"name": "estimate_land_value", "arguments": {"scenario_id": "test", "target_id": 86}})
        assert not result.get("isError"), result
        job = result["structuredContent"]
        status = call("tools/call", {"name": "get_job_status", "arguments": {"job_id": job["job_id"]}})
        assert not status.get("isError"), status
        assert not service.jobs.stopped.is_set()

