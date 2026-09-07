"""Create and configure the Urbanomy MCP server."""
from mcp.server.fastmcp import FastMCP

from urbanomy_agent.service import UrbanomyService
from urbanomy_mcp.tools import register_tools


def build_mcp(service: UrbanomyService) -> FastMCP:
    mcp = FastMCP("urbanomy", stateless_http=True, json_response=True,
                  streamable_http_path="/mcp")
    register_tools(mcp, service)
    return mcp
