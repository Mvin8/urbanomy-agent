"""MCP tool definitions backed by the shared Urbanomy service."""
import asyncio
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from urbanomy_agent.schemas import BlockId, Bounds
from urbanomy_agent.service import UrbanomyService


def register_tools(mcp: FastMCP, service: UrbanomyService) -> None:
    """Register the public tools on a configured MCP server."""
    @mcp.tool()
    def list_scenarios() -> dict[str, Any]:
        """List prepared scenario directories under DATA_DIR. Remote callers cannot open arbitrary server paths."""
        return {"scenarios": service.registry.list()}

    @mcp.tool()
    async def list_blocks(scenario_id: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """List block ids and baseline properties, in pages of up to 200. Never invent a block id. Select scenario_id from list_scenarios."""
        return await asyncio.to_thread(service.list_blocks, scenario_id, offset, limit)

    @mcp.tool()
    async def get_optimization_options(scenario_id: str, target_id: BlockId) -> dict[str, Any]:
        """Get target geometry, indicators, supported constraint names, units and physical limits. Select scenario_id from list_scenarios."""
        return await asyncio.to_thread(service.options, scenario_id, target_id)

    @mcp.tool()
    def estimate_land_value(scenario_id: str, target_id: BlockId, project_id: str | None = None) -> dict[str, Any]:
        """Start land valuation with the pretrained CatBoost model (no LLM). Returns job_id; poll get_job_status. Select scenario_id from list_scenarios. project_id is metadata only."""
        return service.submit("estimate_land_value", dict(scenario_id=scenario_id, target_id=target_id, project_id=project_id))

    @mcp.tool()
    def start_district_optimization(scenario_id: str, target_id: BlockId, strategy: str,
                                    constraints: dict[str, Bounds] | None = None,
                                    use_llm: bool = True, pop_size: int = 20,
                                    n_gen: int = 20, seed: int = 42,
                                    constraints_profile: Literal["test"] | None = None,
                                    project_id: str | None = None) -> dict[str, Any]:
        """Start NSGA-II with hard bounds and an LLM strategy score. Without a profile, omitted variables stay at baseline.
        Profile "test": footprint 1 m² to 10% of site area, floors 1–10, MXI 0.1–1, all shares 0–1.
        Explicit constraints replace profile bounds per parameter. Supply constraints or a profile.
        Select scenario_id from list_scenarios. project_id is metadata only.
        Get options first. strategy contains preferences; constraints contain hard numeric requirements.
        use_llm=false runs two economic objectives only. Returns job_id; use status/result/cancel tools.
        """
        return service.submit("optimize_district", dict(scenario_id=scenario_id, target_id=target_id, project_id=project_id,
            constraints=constraints if constraints is not None else {}, constraints_profile=constraints_profile, strategy=strategy, use_llm=use_llm, pop_size=pop_size, n_gen=n_gen, seed=seed))

    @mcp.tool()
    def get_job_status(job_id: str) -> dict[str, Any]:
        """Get working/completed/failed/canceled state and evaluation progress. Poll every few seconds."""
        return service.jobs.get(job_id)

    @mcp.tool()
    def get_job_result(job_id: str) -> dict[str, Any]:
        """Get completed valuation or Pareto scenarios, summary, effective constraints and provenance."""
        return service.jobs.result(job_id)

    @mcp.tool()
    def get_job_geojson(job_id: str) -> dict[str, Any]:
        """Get WGS84 GeoJSON: valuation for all blocks or alternatives for the selected block."""
        return service.jobs.geojson(job_id)

    @mcp.tool()
    async def cancel_job(job_id: str) -> dict[str, Any]:
        """Stop the job's worker process. Canceling one job does not stop another."""
        return await asyncio.to_thread(service.jobs.cancel, job_id)

