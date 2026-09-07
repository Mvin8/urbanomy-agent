"""One HTTP process exposes both protocols and owns their worker lifecycle."""
from contextlib import asynccontextmanager
import hmac

from fastapi import FastAPI
from starlette.responses import JSONResponse

from .a2a import add_routes
from urbanomy_mcp.server import build_mcp
from .service import UrbanomyService
from .settings import Settings


def build_app(settings=None, service=None):
    settings = settings or Settings()
    service = service or UrbanomyService(settings)
    mcp = build_mcp(service)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_):
        try:
            async with mcp.session_manager.run():
                yield
        finally:
            service.jobs.close()

    app = FastAPI(title="Urbanomy MCP + A2A", lifespan=lifespan)

    @app.middleware("http")
    async def authenticate(request, call_next):
        public_paths = {"/health", "/.well-known/agent-card.json"}
        if settings.token and request.url.path not in public_paths:
            expected = f"Bearer {settings.token}"
            if not hmac.compare_digest(request.headers.get("authorization", ""), expected):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "urbanomy", "protocols": ["mcp", "a2a-1.0"]}

    app.state.service = service
    app.state.a2a_handler = add_routes(app, service)
    # /a2a and discovery routes must precede the root-mounted MCP application.
    app.mount("/", mcp_app)
    return app


def main():
    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()
    settings = Settings()
    uvicorn.run(build_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
