import json
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from app.schemas.llm import LLMMessage, LLMResponse
from config import get_settings


class DeepSeekClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL
        self.embedding_model = settings.DEEPSEEK_EMBEDDING_MODEL
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 256,
        temperature: float = 0.2,
        stream: bool = False,
    ) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

    def _extract_content(self, data: dict) -> str:
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content:
            raise ValueError("模型未返回最终 content（可能只输出了 reasoning_content）")
        return content

    async def _request(self, payload: dict, timeout: int = 60) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            )
        if response.status_code != 200:
            snippet = response.text[:300]
            raise RuntimeError(
                f"DeepSeek API 返回 {response.status_code}: {snippet}"
            )
        return response

    async def chat(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 256,
        temperature: float = 0.2,
    ) -> LLMResponse:
        payload = self._build_payload(messages, max_tokens, temperature, stream=False)
        response = await self._request(payload)
        data = response.json()
        content = self._extract_content(data)
        return LLMResponse(content=content, raw=data)

    async def chat_json(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        max_tokens: int = 256,
        temperature: float = 0.1,
    ) -> BaseModel:
        fields = list(response_model.model_fields.keys())
        field_list = ", ".join(f'"{f}"' for f in fields)
        json_instruction = LLMMessage(
            role="system",
            content=(
                f"请只返回一个 JSON 对象，包含以下字段: {field_list}。"
                "输出必须是纯 JSON，不要加 ``` 标记，不要加任何解释文字。"
            ),
        )
        # system 指令放到最前面
        modified = [json_instruction] + list(messages)
        payload = self._build_payload(modified, max_tokens, temperature, stream=False)
        response = await self._request(payload)
        data = response.json()
        content = self._extract_content(data)
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
        try:
            return response_model.model_validate_json(content)
        except Exception as e:
            raise ValueError(
                f"JSON 解析失败: {e}. 原始内容: {content[:300]}"
            ) from e

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 256,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        payload = self._build_payload(messages, max_tokens, temperature, stream=True)
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    snippet = (await response.aread()).decode()[:300]
                    raise RuntimeError(
                        f"DeepSeek API 返回 {response.status_code}: {snippet}"
                    )
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            text = delta.get("content", "")
                            if text:
                                yield text
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def embed_text(self, text: str) -> list[float]:
        settings = get_settings()
        emb_api_key = settings.EMBEDDING_API_KEY or self.api_key
        emb_base_url = (settings.EMBEDDING_BASE_URL or self.base_url).rstrip("/")
        headers = {
            "Authorization": f"Bearer {emb_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.embedding_model,
            "input": text,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{emb_base_url}/embeddings",
                headers=headers,
                json=payload,
            )
        if response.status_code != 200:
            snippet = response.text[:300]
            raise RuntimeError(
                f"Embedding API 返回 {response.status_code}: {snippet}"
            )
        data = response.json()
        return data["data"][0]["embedding"]
