"""FastAPI app factory."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from tukey.config import ConfigManager
from tukey.storage import Storage
from tukey.server.routes import config as config_routes
from tukey.server.routes import chat as chat_routes
from tukey.server.routes import models as models_routes
from tukey.server.routes import search as search_routes
from tukey.server.routes import experiments as experiment_routes
from tukey.server import websocket as ws_routes

UI_DIST = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"


def create_app(data_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Tukey", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = Storage(data_dir)
    storage.ensure_dirs()
    config = ConfigManager(storage)

    # Wire up route modules
    config_routes.init(config)
    chat_routes.init(storage, config)
    models_routes.init(config)
    search_routes.init(storage)
    experiment_routes.init(storage, config)
    ws_routes.init(storage, config)

    app.include_router(config_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(models_routes.router)
    app.include_router(search_routes.router)
    app.include_router(experiment_routes.router)
    app.include_router(ws_routes.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "data_dir": str(storage.data_dir)}

    # Serve built UI
    if UI_DIST.exists():
        app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            return FileResponse(UI_DIST / "index.html")

    return app
