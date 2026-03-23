"""FastAPI app factory."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel

from tukey import __version__
from tukey.config import ConfigManager
from tukey.storage import Storage, read_global_config, write_global_config
from tukey.server.routes import config as config_routes
from tukey.server.routes import chat as chat_routes
from tukey.server.routes import models as models_routes
from tukey.server.routes import search as search_routes
from tukey.server.routes import experiments as experiment_routes
from tukey.server import websocket as ws_routes

# Installed package: tukey/static/ (populated by CI build)
# Local dev: ui/dist/ (populated by npm run build)
_PKG_STATIC = Path(__file__).resolve().parent.parent / "static"
_DEV_STATIC = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"
UI_DIST = _PKG_STATIC if _PKG_STATIC.exists() else _DEV_STATIC


def _init_routes(storage: Storage, config: ConfigManager) -> None:
    """Wire up all route modules with the given storage/config instances."""
    config_routes.init(config)
    chat_routes.init(storage, config)
    models_routes.init(config)
    search_routes.init(storage)
    experiment_routes.init(storage, config)
    ws_routes.init(storage, config)


class _AppState:
    """Mutable holder so the health/switch endpoints always see the current instances."""
    def __init__(self, storage: Storage, config: ConfigManager):
        self.storage = storage
        self.config = config


class DataDirRequest(BaseModel):
    data_dir: str


def create_app(data_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Tukey", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Resolve data_dir: CLI flag > global config > default
    if data_dir is None:
        global_cfg = read_global_config()
        data_dir = global_cfg.get("data_dir")

    storage = Storage(data_dir)
    storage.ensure_dirs()
    config = ConfigManager(storage)
    state = _AppState(storage, config)

    _init_routes(storage, config)

    app.include_router(config_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(models_routes.router)
    app.include_router(search_routes.router)
    app.include_router(experiment_routes.router)
    app.include_router(ws_routes.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "data_dir": str(state.storage.data_dir)}

    @app.post("/api/config/data-dir")
    def switch_data_dir(body: DataDirRequest):
        """Switch the active data directory at runtime."""
        new_dir = body.data_dir.strip()
        if not new_dir:
            raise HTTPException(400, "data_dir must not be empty")

        new_storage = Storage(new_dir)
        new_storage.ensure_dirs()
        new_config = ConfigManager(new_storage)

        # Re-wire all route modules
        _init_routes(new_storage, new_config)
        state.storage = new_storage
        state.config = new_config

        # Persist choice for next startup
        global_cfg = read_global_config()
        global_cfg["data_dir"] = str(new_storage.data_dir)
        write_global_config(global_cfg)

        return {"status": "ok", "data_dir": str(new_storage.data_dir)}

    # Serve built UI
    if UI_DIST.exists():
        app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")
        logos_dir = UI_DIST / "logos"
        if logos_dir.exists():
            app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")

        @app.get("/favicon-light.svg")
        async def favicon_light():
            return FileResponse(UI_DIST / "favicon-light.svg")

        @app.get("/favicon-dark.svg")
        async def favicon_dark():
            return FileResponse(UI_DIST / "favicon-dark.svg")

        @app.get("/icons.svg")
        async def icons():
            return FileResponse(UI_DIST / "icons.svg")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            return FileResponse(UI_DIST / "index.html")

    return app
