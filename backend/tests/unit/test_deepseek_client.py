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
