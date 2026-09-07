"""Run Urbanomy MCP over stdio."""
from urbanomy_agent.service import UrbanomyService
from urbanomy_agent.settings import Settings
from urbanomy_mcp.server import build_mcp


def main():
    from dotenv import load_dotenv

    load_dotenv()
    service = UrbanomyService(Settings())
    try:
        build_mcp(service).run(transport="stdio")
    finally:
        service.jobs.close()


if __name__ == "__main__":
    main()
