import pytest

from app.schemas.llm import LLMMessage, SlotExtractionResult
from app.services.deepseek_client import DeepSeekClient
from config import get_settings


@pytest.fixture(scope="module")
def client():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置，跳过真实 AI 测试")
    try:
        return DeepSeekClient()
    except ValueError as e:
        pytest.skip(str(e))


@pytest.mark.ai
@pytest.mark.integration
async def test_deepseek_chat_real_api(client):
    response = await client.chat(
        [LLMMessage(role="user", content="1+1等于几？只回答数字。")],
        max_tokens=200,
        temperature=0.0,
    )
    assert response.content
    assert "2" in response.content


@pytest.mark.ai
@pytest.mark.integration
async def test_deepseek_chat_json_real_api(client):
    result = await client.chat_json(
        [LLMMessage(role="user", content='提取行业和产品："我们是一家做健身器材的工厂"。')],
        response_model=SlotExtractionResult,
        max_tokens=300,
        temperature=0.0,
    )
    assert isinstance(result, SlotExtractionResult)
    assert result.industry is not None or result.main_product is not None
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.ai
@pytest.mark.integration
async def test_deepseek_stream_chat_real_api(client):
    chunks: list[str] = []
    async for chunk in client.stream_chat(
        [LLMMessage(role="user", content="2+2等于几？")],
        max_tokens=200,
        temperature=0.0,
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    full = "".join(chunks)
    assert "4" in full
