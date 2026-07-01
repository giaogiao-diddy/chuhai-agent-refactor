import pytest
from httpx import Response, Request

from app.schemas.llm import LLMMessage
from app.schemas.report import RawAIReport
from app.services.deepseek_client import DeepSeekClient


class _FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def json(self):
        return self._data


@pytest.mark.asyncio
async def test_chat_json_raises_on_finish_reason_length(monkeypatch):
    """finish_reason="length" → ValueError（不调真实 API，不读真实 key）。"""
    from config import Settings

    monkeypatch.setattr(
        "app.services.deepseek_client.get_settings",
        lambda: Settings(
            DEEPSEEK_API_KEY="fake-key",
            DEEPSEEK_MODEL="deepseek-test",
            DEEPSEEK_EMBEDDING_MODEL="embedding-test",
            DEEPSEEK_BASE_URL="https://example.com",
        ),
    )

    async def _fake_request(self, payload, timeout=60):
        return _FakeResponse({
            "choices": [{
                "finish_reason": "length",
                "message": {"content": '{"summary_conclusion":"x"'},
            }]
        })

    monkeypatch.setattr(DeepSeekClient, "_request", _fake_request)

    client = DeepSeekClient()
    messages = [LLMMessage(role="user", content="生成报告")]
    with pytest.raises(ValueError, match="finish_reason=length"):
        await client.chat_json(messages, response_model=RawAIReport, max_tokens=100)


@pytest.mark.asyncio
async def test_stream_chat_raises_on_finish_reason_length(monkeypatch):
    """stream_chat 中 finish_reason=length → ValueError。"""
    from config import Settings

    monkeypatch.setattr(
        "app.services.deepseek_client.get_settings",
        lambda: Settings(
            DEEPSEEK_API_KEY="fake-key",
            DEEPSEEK_MODEL="deepseek-test",
            DEEPSEEK_EMBEDDING_MODEL="embedding-test",
            DEEPSEEK_BASE_URL="https://example.com",
        ),
    )

    class _FakeStreamResponse:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass

        def __init__(self, status_code=200):
            self.status_code = status_code

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":null,"reasoning_content":"..."},"finish_reason":"length"}]}'
            yield "data: [DONE]"

    class _FakeStreamClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        def stream(self, method, url, headers, json, **kw):
            return _FakeStreamResponse()

    monkeypatch.setattr("httpx.AsyncClient", _FakeStreamClient)

    client = DeepSeekClient()
    messages = [LLMMessage(role="user", content="test")]
    with pytest.raises(ValueError, match="finish_reason=length"):
        async for _ in client.stream_chat(messages, max_tokens=100):
            pass
