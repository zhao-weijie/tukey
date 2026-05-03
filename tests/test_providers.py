"""Tests for the provider module."""

import base64

import httpx
import pytest
from tukey.providers.base import ImageResponse, LLMResponse, StreamChunk
from tukey.providers.openai_provider import OpenAICompatibleProvider


def test_llm_response_defaults():
    r = LLMResponse()
    assert r.content == ""
    assert r.tokens_in == 0
    assert r.cost is None


def test_image_response_defaults():
    r = ImageResponse()
    assert r.images == []
    assert r.content == ""
    assert r.cost is None


def test_stream_chunk():
    c = StreamChunk(delta="hello")
    assert c.delta == "hello"
    assert c.done is False
    assert c.response is None

    r = LLMResponse(content="hello world", tokens_out=10)
    c2 = StreamChunk(delta="", done=True, response=r)
    assert c2.done is True
    assert c2.response.tokens_out == 10


def test_chat_payload_accepts_multimodal_content_arrays():
    provider = OpenAICompatibleProvider(strip_model_prefix=True)

    payload = provider._build_payload("openai/test-model", [{
        "role": "user",
        "content": [
            {"type": "text", "text": "describe"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ],
    }])

    assert payload["model"] == "test-model"
    assert payload["messages"][0]["content"][1]["type"] == "image_url"


@pytest.mark.asyncio
async def test_parse_openrouter_image_response_data_url():
    raw = base64.b64encode(b"png-bytes").decode("ascii")
    async with httpx.AsyncClient() as client:
        response = await OpenAICompatibleProvider._openrouter_image_response({
            "choices": [{
                "message": {
                    "content": "generated",
                    "images": [{
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{raw}"},
                    }],
                },
            }],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3},
        }, "google/gemini-3-pro-image-preview", 12.0, client)

    assert response.content == "generated"
    assert response.images[0].data == b"png-bytes"
    assert response.images[0].mime_type == "image/png"
    assert response.usage["input_tokens"] == 2


@pytest.mark.asyncio
async def test_parse_native_openai_image_response_b64_json():
    raw = base64.b64encode(b"webp-bytes").decode("ascii")
    async with httpx.AsyncClient() as client:
        response = await OpenAICompatibleProvider._native_image_response({
            "data": [{
                "b64_json": raw,
                "output_format": "webp",
                "revised_prompt": "a better prompt",
            }],
            "usage": {"output_tokens": 10},
        }, "gpt-image-2", 14.0, client)

    assert response.content == "a better prompt"
    assert response.images[0].data == b"webp-bytes"
    assert response.images[0].mime_type == "image/webp"
    assert response.usage["output_tokens"] == 10


@pytest.mark.asyncio
async def test_parse_hosted_https_image_response():
    def handler(request):
        assert str(request.url) == "https://images.example/result.png"
        return httpx.Response(200, content=b"hosted-png", headers={"content-type": "image/png"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await OpenAICompatibleProvider._native_image_response({
            "data": [{"url": "https://images.example/result.png"}],
        }, "gpt-image-2", 9.0, client)

    assert response.images[0].data == b"hosted-png"
    assert response.images[0].mime_type == "image/png"


@pytest.mark.asyncio
async def test_hosted_https_image_rejects_non_image_content_type():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"nope", headers={"content-type": "text/html"})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match="non-image"):
            await OpenAICompatibleProvider._native_image_response({
                "data": [{"url": "https://images.example/not-image"}],
            }, "gpt-image-2", 9.0, client)


@pytest.mark.asyncio
async def test_native_image_edit_uses_multipart(monkeypatch):
    raw = base64.b64encode(b"edited").decode("ascii")
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            captured["files"] = kwargs.get("files")
            captured["headers"] = kwargs.get("headers")
            return httpx.Response(
                200,
                json={"data": [{"b64_json": raw}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("tukey.providers.openai_provider.httpx.AsyncClient", lambda: FakeClient())
    provider = OpenAICompatibleProvider(api_key="sk-test", base_url="https://api.example/v1")

    response = await provider.edit_image([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "brighten"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(b'source').decode('ascii')}"
                    },
                },
            ],
        },
    ], "gpt-image-1")

    assert captured["url"] == "https://api.example/v1/images/edits"
    assert captured["data"]["prompt"] == "brighten"
    assert captured["files"][0][0] == "image"
    assert captured["headers"] == {"Authorization": "Bearer sk-test"}
    assert response.images[0].data == b"edited"


@pytest.mark.asyncio
async def test_native_image_generation_posts_prompt_json(monkeypatch):
    raw = base64.b64encode(b"generated").decode("ascii")
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["headers"] = kwargs.get("headers")
            return httpx.Response(
                200,
                json={"data": [{"b64_json": raw}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("tukey.providers.openai_provider.httpx.AsyncClient", lambda: FakeClient())
    provider = OpenAICompatibleProvider(api_key="sk-test", base_url="https://api.example/v1")

    response = await provider.generate_image([
        {
            "role": "user",
            "content": [{"type": "text", "text": "paint a lighthouse"}],
        },
    ], "gpt-image-1", extra_params={"quality": "low"})

    assert captured["url"] == "https://api.example/v1/images/generations"
    assert captured["json"]["prompt"] == "paint a lighthouse"
    assert captured["json"]["quality"] == "low"
    assert captured["json"]["response_format"] == "b64_json"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert response.images[0].data == b"generated"


@pytest.mark.asyncio
async def test_openrouter_image_generation_posts_multimodal_chat(monkeypatch):
    raw = base64.b64encode(b"openrouter-image").decode("ascii")
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            return httpx.Response(
                200,
                json={
                    "choices": [{
                        "message": {
                            "content": "ok",
                            "images": [{
                                "image_url": {"url": f"data:image/png;base64,{raw}"},
                            }],
                        },
                    }],
                },
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("tukey.providers.openai_provider.httpx.AsyncClient", lambda: FakeClient())
    provider = OpenAICompatibleProvider(base_url="https://openrouter.example/api/v1", provider_type="openrouter")

    response = await provider.generate_image([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "vary this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ],
        },
    ], "google/gemini-3-pro-image-preview")

    assert captured["url"] == "https://openrouter.example/api/v1/chat/completions"
    assert captured["json"]["modalities"] == ["image", "text"]
    assert captured["json"]["messages"][0]["content"][1]["type"] == "image_url"
    assert response.images[0].data == b"openrouter-image"
