"""Provider-agnostic AI client.

Talks to any OpenAI-compatible chat-completions endpoint (OpenAI, OpenRouter,
Groq, Together, local Ollama, ...) with plain aiohttp — no heavy SDKs.
Configured entirely from the database, so ``.aiconfig`` changes apply live.

DB keys (owner ``ai``):
    base_url  — e.g. https://api.openai.com/v1 (default)
    api_key   — bearer token
    model     — e.g. gpt-4o-mini (default)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import aiohttp

if TYPE_CHECKING:
    from haruka.core.database import Database

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=120)


class AIError(RuntimeError):
    """Raised when the provider cannot fulfil a request."""


class AIProvider:
    def __init__(self, db: "Database"):
        self.db = db

    # -- config ----------------------------------------------------------

    @property
    def base_url(self) -> str:
        return (self.db.get("ai", "base_url") or DEFAULT_BASE_URL).rstrip("/")

    @property
    def api_key(self) -> Optional[str]:
        return self.db.get("ai", "api_key")

    @property
    def model(self) -> str:
        return self.db.get("ai", "model") or DEFAULT_MODEL

    @property
    def is_configured(self) -> bool:
        # Local endpoints (Ollama etc.) may not need a key.
        return bool(self.api_key) or "localhost" in self.base_url or "127.0.0.1" in self.base_url

    # -- requests ----------------------------------------------------------

    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """One-shot chat completion. Raises :class:`AIError` on any failure."""
        if not self.is_configured:
            raise AIError(
                "AI is not configured. Set a key with .aiconfig key <token> "
                "(and optionally .aiconfig url / .aiconfig model)."
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200:
                        detail = (
                            data.get("error", {}).get("message", "")
                            if isinstance(data, dict)
                            else ""
                        )
                        raise AIError(f"Provider returned {resp.status}: {detail[:200]}")
        except aiohttp.ClientError as exc:
            raise AIError(f"Network error: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Unexpected response shape from provider.") from exc
