from __future__ import annotations

from haruka.telegram.bot_api import BotAPIClient, BotAPIConfig


def test_bot_api_config() -> None:
    client = BotAPIClient(BotAPIConfig("token"))
    assert client.config.api_base == "https://api.telegram.org"
    assert client.config.max_retries == 3
