"""Shared test fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tukey.storage import Storage
from tukey.config import ConfigManager
from tukey.server.app import create_app


@pytest.fixture
def storage(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    return s


@pytest.fixture
def config(storage: Storage):
    cm = ConfigManager(storage)
    cm.add_provider("openai", "sk-test", base_url="http://localhost:9999")
    return cm


@pytest.fixture
def app(tmp_path: Path):
    return create_app(data_dir=str(tmp_path / "appdata"))


@pytest.fixture
def client(app):
    return TestClient(app)
