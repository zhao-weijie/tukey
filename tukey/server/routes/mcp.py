"""FastAPI routes for MCP server management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.config import ConfigManager
from tukey.mcp.manager import McpManager

router = APIRouter(prefix="/api/config/mcp-servers", tags=["mcp"])

_config: ConfigManager | None = None
_mcp_manager: McpManager | None = None


def init(config: ConfigManager, mcp_manager: McpManager) -> None:
    global _config, _mcp_manager
    _config = config
    _mcp_manager = mcp_manager


def _cm() -> ConfigManager:
    assert _config is not None
    return _config


def _mm() -> McpManager:
    assert _mcp_manager is not None
    return _mcp_manager


class McpServerCreate(BaseModel):
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


class McpServerUpdate(BaseModel):
    name: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    enabled: bool | None = None


@router.get("")
def list_mcp_servers():
    return _cm().list_mcp_servers()


@router.get("/{server_id}")
def get_mcp_server(server_id: str):
    s = _cm().get_mcp_server(server_id)
    if not s:
        raise HTTPException(404, "MCP server not found")
    return s


@router.post("", status_code=201)
def create_mcp_server(body: McpServerCreate):
    return _cm().add_mcp_server(
        name=body.name,
        command=body.command,
        args=body.args,
        env=body.env,
    )


@router.patch("/{server_id}")
def update_mcp_server(server_id: str, body: McpServerUpdate):
    updates = body.model_dump(exclude_none=True)
    result = _cm().update_mcp_server(server_id, updates)
    if not result:
        raise HTTPException(404, "MCP server not found")
    # If command/args/env changed, stop the running server so it restarts fresh
    if any(k in updates for k in ("command", "args", "env")):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_mm().stop_server(server_id))
            else:
                loop.run_until_complete(_mm().stop_server(server_id))
        except Exception:
            pass
    return result


@router.delete("/{server_id}", status_code=204)
async def delete_mcp_server(server_id: str):
    await _mm().stop_server(server_id)
    if not _cm().remove_mcp_server(server_id):
        raise HTTPException(404, "MCP server not found")


@router.post("/{server_id}/test")
async def test_mcp_server(server_id: str):
    """Start the MCP server, discover tools, then stop. Returns tool list."""
    s = _cm().get_mcp_server(server_id)
    if not s:
        raise HTTPException(404, "MCP server not found")

    from tukey.mcp.client import McpClient

    client = McpClient(s)
    try:
        await client.start()
        tools = [
            {"name": t["function"]["name"], "description": t["function"].get("description", "")}
            for t in client.tools
        ]
        return {"ok": True, "tools": tools}
    except Exception as e:
        return {"ok": False, "error": str(e), "tools": []}
    finally:
        await client.stop()
