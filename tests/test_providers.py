"""Tests for the provider module."""

import pytest
from tukey.providers.base import LLMResponse, StreamChunk


def test_llm_response_defaults():
    r = LLMResponse()
    assert r.content == ""
    assert r.tokens_in == 0
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
