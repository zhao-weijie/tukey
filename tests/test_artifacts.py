from __future__ import annotations

import hashlib

import pytest

from tukey.core import contracts


def _create_run(storage):
    config_set = contracts.make_config_set({"name": "Artifact Set"})
    storage.write_config_set_meta(config_set["id"], config_set)
    run = contracts.make_run({
        "name": "Artifact Run",
        "config_set_id": config_set["id"],
    })
    storage.write_run_record_meta(run["id"], run)
    return run


def test_write_and_read_artifact_bytes(storage):
    run = _create_run(storage)

    artifact = storage.write_artifact_bytes(
        run["id"],
        b"image bytes",
        kind="output",
        modality="image",
        mime_type="image/png",
    )

    assert artifact["filename"].endswith(".png")
    assert artifact["size_bytes"] == len(b"image bytes")
    assert artifact["sha256"] == hashlib.sha256(b"image bytes").hexdigest()
    assert artifact["path"].startswith(f"runs/{run['id']}/artifacts/")
    assert storage.read_artifact_bytes(artifact) == b"image bytes"
    assert storage.find_artifact_meta(artifact["id"]) == artifact


def test_artifact_filename_rejects_path_escape(storage):
    run = _create_run(storage)

    with pytest.raises(ValueError, match="must not include a path"):
        storage.write_artifact_bytes(
            run["id"],
            b"bad",
            kind="output",
            modality="image",
            mime_type="image/png",
            filename="../bad.png",
        )


def test_artifact_file_path_rejects_path_escape(storage):
    run = _create_run(storage)

    with pytest.raises(ValueError, match="escapes"):
        storage.artifact_file_path(run["id"], "../bad.png")


def test_artifact_content_endpoint_serves_bytes(client):
    provider = client.post("/api/config/providers", json={
        "provider": "openai",
        "api_key": "sk-artifact",
        "base_url": "https://example.test/v1",
    }).json()
    config_set = client.post("/api/config-sets", json={"name": "Artifact Routes"}).json()
    client.post(f"/api/config-sets/{config_set['id']}/slots", json={
        "provider_id": provider["id"],
        "provider_model_id": "openai/test-model",
    })
    run = client.post("/api/runs", json={
        "name": "Artifact Route Run",
        "config_set_id": config_set["id"],
    }).json()

    storage = client.app.state.tukey.storage
    artifact = storage.write_artifact_bytes(
        run["id"],
        b"route-image",
        kind="output",
        modality="image",
        mime_type="image/png",
    )

    response = client.get(f"/api/artifacts/{artifact['id']}/content")

    assert response.status_code == 200
    assert response.content == b"route-image"
    assert response.headers["content-type"] == "image/png"
