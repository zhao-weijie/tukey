"""Tests for the config manager."""

from pathlib import Path

from tukey.storage import Storage
from tukey.config import ConfigManager


def test_load_empty(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cm = ConfigManager(s)
    cfg = cm.load()
    assert cfg == {"providers": []}


def test_add_provider(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cm = ConfigManager(s)
    p = cm.add_provider("openai", "sk-test", base_url="http://localhost")
    assert p["provider"] == "openai"
    assert p["api_key"] == "sk-test"
    assert p["base_url"] == "http://localhost"
    assert "id" in p

    providers = cm.list_providers()
    assert len(providers) == 1
    assert providers[0]["id"] == p["id"]


def test_get_provider(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cm = ConfigManager(s)
    p = cm.add_provider("anthropic", "sk-ant")
    assert cm.get_provider(p["id"]) == p
    assert cm.get_provider("nonexistent") is None


def test_update_provider(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cm = ConfigManager(s)
    p = cm.add_provider("openai", "sk-old")
    updated = cm.update_provider(p["id"], {"api_key": "sk-new"})
    assert updated["api_key"] == "sk-new"
    assert cm.get_provider(p["id"])["api_key"] == "sk-new"


def test_remove_provider(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cm = ConfigManager(s)
    p = cm.add_provider("openai", "sk-test")
    assert cm.remove_provider(p["id"]) is True
    assert cm.list_providers() == []
    assert cm.remove_provider("nonexistent") is False
