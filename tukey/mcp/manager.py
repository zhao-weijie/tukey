"""McpManager — manages lifecycle of all MCP server subprocesses."""

from __future__ import annotations

import logging
from typing import Any

from tukey.mcp.client import McpClient

log = logging.getLogger(__name__)


class McpManager:
    """Holds all active McpClient instances; lazy-starts servers on demand."""

    def __init__(self) -> None:
        self.clients: dict[str, McpClient] = {}  # server_id -> client

    async def ensure_running(self, server_config: dict[str, Any]) -> McpClient:
        """Start server if not running, restart if dead. Returns the client."""
        sid = server_config["id"]

        if sid in self.clients:
            client = self.clients[sid]
            if client.running:
                return client
            # Dead process — clean up and restart
            log.warning("MCP server %s died, restarting", server_config["name"])
            await client.stop()
            del self.clients[sid]

        client = McpClient(server_config)
        await client.start()
        self.clients[sid] = client
        return client

    async def get_tools(
        self, server_ids: list[str], config_manager: Any
    ) -> list[dict[str, Any]]:
        """Get merged OpenAI-format tools from specified servers, starting as needed."""
        tools: list[dict[str, Any]] = []
        for sid in server_ids:
            cfg = config_manager.get_mcp_server(sid)
            if not cfg or not cfg.get("enabled", True):
                continue
            client = await self.ensure_running(cfg)
            tools.extend(client.tools)
        return tools

    def get_tool_routing(self, server_ids: list[str]) -> dict[str, str]:
        """Map tool_name -> server_id for execution routing."""
        routing: dict[str, str] = {}
        for sid in server_ids:
            client = self.clients.get(sid)
            if client:
                for tool in client.tools:
                    routing[tool["function"]["name"]] = sid
        return routing

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool via the correct MCP server."""
        client = self.clients.get(server_id)
        if not client or not client.running:
            raise RuntimeError(f"MCP server {server_id} not running")
        return await client.call_tool(tool_name, arguments)

    async def stop_server(self, server_id: str) -> None:
        """Stop a specific server."""
        client = self.clients.pop(server_id, None)
        if client:
            await client.stop()

    async def shutdown_all(self) -> None:
        """Stop all running MCP servers."""
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()
        log.info("All MCP servers shut down")
