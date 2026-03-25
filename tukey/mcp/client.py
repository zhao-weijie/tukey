"""McpClient — manages a single MCP server subprocess via stdio JSON-RPC."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

log = logging.getLogger(__name__)


class McpClient:
    """Manages one MCP server subprocess using stdio transport (JSON-RPC 2.0)."""

    def __init__(self, config: dict[str, Any]):
        self.config = config  # {id, name, command, args, env, enabled}
        self.process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._reader_task: asyncio.Task | None = None
        self.tools: list[dict[str, Any]] = []  # cached OpenAI-format tools
        self._tool_names: set[str] = set()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def start(self) -> None:
        """Spawn subprocess, run MCP initialize handshake, discover tools."""
        command = self.config["command"]
        args = self.config.get("args", [])

        # On Windows, npx needs .cmd extension
        if sys.platform == "win32" and command in ("npx", "node", "npm"):
            command = f"{command}.cmd"

        env = {**os.environ, **(self.config.get("env") or {})}

        log.info("Starting MCP server %s: %s %s", self.config["name"], command, args)
        self.process = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._read_loop())

        # Initialize handshake
        result = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tukey", "version": "0.4.0"},
        })
        log.info("MCP server %s initialized: %s", self.config["name"], result.get("serverInfo"))
        await self._notify("notifications/initialized", {})

        # Discover tools
        tools_result = await self._request("tools/list", {})
        mcp_tools = tools_result.get("tools", [])
        self.tools = [self._to_openai_format(t) for t in mcp_tools]
        self._tool_names = {t["function"]["name"] for t in self.tools}
        log.info("MCP server %s: %d tools discovered", self.config["name"], len(self.tools))

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return the result as text."""
        result = await self._request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        content_parts = result.get("content", [])
        texts = [p.get("text", "") for p in content_parts if p.get("type") == "text"]
        return "\n".join(texts)

    def has_tool(self, name: str) -> bool:
        return name in self._tool_names

    async def stop(self) -> None:
        """Graceful shutdown."""
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        if self.process and self.process.returncode is None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                self.process.kill()
        self._pending.clear()
        log.info("MCP server %s stopped", self.config["name"])

    # --- JSON-RPC helpers ---

    async def _request(self, method: str, params: dict) -> dict:
        self._request_id += 1
        req_id = self._request_id
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        assert self.process and self.process.stdin
        self.process.stdin.write((json.dumps(msg) + "\n").encode())
        await self.process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise RuntimeError(f"MCP request {method} timed out after 30s")

    async def _notify(self, method: str, params: dict) -> None:
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        assert self.process and self.process.stdin
        self.process.stdin.write((json.dumps(msg) + "\n").encode())
        await self.process.stdin.drain()

    async def _read_loop(self) -> None:
        """Read JSON-RPC responses from stdout, route to pending futures."""
        assert self.process and self.process.stdout
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                except json.JSONDecodeError:
                    log.warning("MCP non-JSON line: %s", line_str[:200])
                    continue

                req_id = data.get("id")
                if req_id is not None and req_id in self._pending:
                    if "error" in data:
                        err = data["error"]
                        self._pending[req_id].set_exception(
                            RuntimeError(f"MCP error ({err.get('code')}): {err.get('message')}")
                        )
                    else:
                        self._pending[req_id].set_result(data.get("result", {}))
                    del self._pending[req_id]
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("MCP read loop error: %s", e)
        finally:
            # Fail all pending futures
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("MCP server disconnected"))
            self._pending.clear()

    @staticmethod
    def _to_openai_format(mcp_tool: dict) -> dict:
        """Convert MCP tool schema to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool.get("description", ""),
                "parameters": mcp_tool.get("inputSchema", {
                    "type": "object", "properties": {},
                }),
            },
        }
