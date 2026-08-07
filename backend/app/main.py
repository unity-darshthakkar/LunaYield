from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    application = FastAPI(
        title="LunaYield Mission Lab",
        version="1.0.0",
        description="Lunar rover operations and mission-planning platform.",
    )
    application.include_router(health.router)
    return application


app = create_app()
