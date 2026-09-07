"""MCP tool definitions backed by the shared Urbanomy service."""
import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from urbanomy_agent.schemas import BlockId, Bounds
from urbanomy_agent.service import UrbanomyService


def register_tools(mcp: FastMCP, service: UrbanomyService) -> None:
    """Register the public tools on a configured MCP server."""
    @mcp.tool()
    def list_datasets() -> dict[str, Any]:
        """List registered datasets. Remote callers cannot open arbitrary server paths."""
        return {"datasets": service.registry.list()}

    @mcp.tool()
    async def list_blocks(dataset_id: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """List block ids and baseline properties, in pages of up to 200. Never invent a block id."""
        return await asyncio.to_thread(service.list_blocks, dataset_id, offset, limit)

    @mcp.tool()
    async def get_optimization_options(dataset_id: str, target_id: BlockId) -> dict[str, Any]:
        """Get target geometry, indicators, supported constraint names, units and physical limits."""
        return await asyncio.to_thread(service.options, dataset_id, target_id)

    @mcp.tool()
    def estimate_land_value(dataset_id: str, target_id: BlockId) -> dict[str, Any]:
        """Start land valuation with the pretrained CatBoost model (no LLM). Returns job_id; poll get_job_status."""
        return service.submit("estimate_land_value", dict(dataset_id=dataset_id, target_id=target_id))

    @mcp.tool()
    def start_district_optimization(dataset_id: str, target_id: BlockId, constraints: dict[str, Bounds],
                                    strategy: str, use_llm: bool = True, pop_size: int = 20,
                                    n_gen: int = 20, seed: int = 42) -> dict[str, Any]:
        """Start NSGA-II with hard bounds and an LLM strategy score. Omitted variables stay at baseline.
        Get options first. strategy contains preferences; constraints contain hard numeric requirements.
        use_llm=false runs two economic objectives only. Returns job_id; use status/result/cancel tools.
        """
        return service.submit("optimize_district", dict(dataset_id=dataset_id, target_id=target_id,
            constraints=constraints, strategy=strategy, use_llm=use_llm, pop_size=pop_size, n_gen=n_gen, seed=seed))

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

