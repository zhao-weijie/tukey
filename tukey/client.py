"""Sync SDK client for the Tukey API."""

from __future__ import annotations

from typing import Any

import httpx


class TukeyClient:
    """Synchronous client wrapping Tukey's REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ):
        self._client = http_client or httpx.Client(base_url=base_url, **kwargs)

    def __enter__(self) -> TukeyClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        r = self._client.request(method, path, **kwargs)
        r.raise_for_status()
        if r.status_code == 204:
            return None
        return r.json()

    # --- Providers ---

    def list_providers(self) -> list[dict]:
        return self._request("GET", "/api/config/providers")

    def create_provider(self, provider: str, api_key: str, **kwargs: Any) -> dict:
        body = {"provider": provider, "api_key": api_key, **kwargs}
        return self._request("POST", "/api/config/providers", json=body)

    def delete_provider(self, provider_id: str) -> None:
        self._request("DELETE", f"/api/config/providers/{provider_id}")

    # --- Chatrooms ---

    def list_chatrooms(self) -> list[dict]:
        return self._request("GET", "/api/chat/chatrooms")

    def create_chatroom(self, name: str, models: list[dict] | None = None) -> dict:
        body: dict[str, Any] = {"name": name}
        if models:
            body["models"] = models
        return self._request("POST", "/api/chat/chatrooms", json=body)

    def get_chatroom(self, chatroom_id: str) -> dict:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}")

    def update_chatroom(self, chatroom_id: str, **kwargs: Any) -> dict:
        return self._request("PATCH", f"/api/chat/chatrooms/{chatroom_id}", json=kwargs)

    def delete_chatroom(self, chatroom_id: str) -> None:
        self._request("DELETE", f"/api/chat/chatrooms/{chatroom_id}")

    # --- Chats ---

    def list_chats(self, chatroom_id: str) -> list[dict]:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}/chats")

    def create_chat(self, chatroom_id: str, name: str | None = None) -> dict:
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        return self._request("POST", f"/api/chat/chatrooms/{chatroom_id}/chats", json=body)

    def get_chat(self, chatroom_id: str, chat_id: str) -> dict:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}")

    def delete_chat(self, chatroom_id: str, chat_id: str) -> None:
        self._request("DELETE", f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}")

    # --- Messages ---

    def send_message(self, chatroom_id: str, chat_id: str, content: str) -> dict:
        return self._request(
            "POST",
            f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/messages",
            json={"content": content},
        )

    def get_messages(self, chatroom_id: str, chat_id: str) -> list[dict]:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/messages")

    # --- Reproducibility ---

    def get_manifest(self, chatroom_id: str, chat_id: str) -> dict:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/manifest")

    def replay_chat(self, chatroom_id: str, chat_id: str) -> dict:
        return self._request("POST", f"/api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/replay")

    # --- Export / Import ---

    def export_chatroom(self, chatroom_id: str) -> dict:
        return self._request("GET", f"/api/chat/chatrooms/{chatroom_id}/export")

    def import_chatroom(self, data: dict) -> dict:
        return self._request("POST", "/api/chat/chatrooms/import", json={"data": data})

    # --- Batch helper ---

    def run_batch(self, chatroom_id: str, prompts: list[str]) -> tuple[dict, list[dict]]:
        chat = self.create_chat(chatroom_id)
        turns = []
        for prompt in prompts:
            turn = self.send_message(chatroom_id, chat["id"], prompt)
            turns.append(turn)
        return chat, turns
