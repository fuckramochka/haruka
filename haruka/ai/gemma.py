from __future__ import annotations

import aiohttp

from haruka.ai.provider import ChatMessage, ModelProvider
from haruka.config.settings import Settings


class GoogleGemmaProvider(ModelProvider):
    """OpenAI-compatible adapter for Google Gemma 4 31B IT deployments."""

    def __init__(self, settings: Settings):
        if not settings.gemma_api_key:
            raise ValueError("GEMMA_API_KEY is required")
        if not settings.gemma_api_base:
            raise ValueError("GEMMA_API_BASE is required")
        self.settings = settings

    async def complete(self, messages: list[ChatMessage]) -> str:
        url = f"{self.settings.gemma_api_base}/chat/completions"
        payload = {
            "model": self.settings.gemma_model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": self.settings.ai_temperature,
            "max_tokens": self.settings.ai_max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.gemma_api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload, timeout=60) as response:
                response.raise_for_status()
                data = await response.json()
        return data["choices"][0]["message"]["content"].strip()

