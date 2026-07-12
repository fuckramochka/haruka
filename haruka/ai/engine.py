from __future__ import annotations

from haruka.ai.gemma import GoogleGemmaProvider
from haruka.ai.provider import ChatMessage, ModelProvider
from haruka.config.settings import Settings
from haruka.domain import ChatStyleProfile, EmotionState, IncomingMessage
from haruka.goals.engine import Goal
from haruka.personality.engine import PersonalityEngine


class AIEngine:
    def __init__(self, provider: ModelProvider, personality: PersonalityEngine):
        self.provider = provider
        self.personality = personality

    @classmethod
    def from_settings(cls, settings: Settings, personality: PersonalityEngine) -> "AIEngine":
        if settings.ai_provider != "google_gemma":
            raise ValueError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")
        return cls(GoogleGemmaProvider(settings), personality)

    async def generate_reply(
        self,
        message: IncomingMessage,
        people_memory: dict,
        self_memory: dict,
        world_memory: dict,
        style_profile: ChatStyleProfile | None,
        emotion: EmotionState,
        recalled_memories: list[dict],
        relationship: dict | None = None,
        active_goals: list[Goal] | None = None,
        relevant_lore: list[dict] | None = None,
        long: bool = False,
    ) -> str:
        system = self.personality.system_prompt(
            people_memory=people_memory,
            self_memory=self_memory,
            world_memory=world_memory,
            style_profile=style_profile,
            emotion=emotion,
            relationship=relationship or {},
            active_goals=active_goals or [],
            relevant_lore=relevant_lore or [],
            long=long,
        )
        memory_text = "\n".join(f"- {item['text']}" for item in recalled_memories[:5])
        user = (
            f"Incoming Telegram message from {message.sender_name or 'unknown'} "
            f"in {message.chat_title or 'private chat'}:\n{message.text}\n\n"
            f"Relevant memories:\n{memory_text or '- none'}\n\n"
            "Reply as Haruka only if it feels natural. Do not explain your reasoning."
        )
        return await self.provider.complete(
            [ChatMessage("system", system), ChatMessage("user", user)]
        )

    async def generate_initiative(
        self,
        chat_title: str | None,
        self_memory: dict,
        world_memory: dict,
        style_profile: ChatStyleProfile | None,
        emotion: EmotionState,
        active_goal: Goal | None,
        lore_seed: dict | None,
    ) -> str:
        system = self.personality.system_prompt(
            people_memory={},
            self_memory=self_memory,
            world_memory=world_memory,
            style_profile=style_profile,
            emotion=emotion,
            relationship={},
            active_goals=[active_goal] if active_goal else [],
            relevant_lore=[lore_seed] if lore_seed else [],
            long=False,
        )
        user = (
            f"Telegram chat: {chat_title or 'unknown'}.\n"
            f"Haruka may write first only if it feels socially plausible.\n"
            f"Current goal: {active_goal.title if active_goal else 'none'}.\n"
            f"Lore seed: {lore_seed or 'none'}.\n"
            "Write one short natural message, or return an empty string if silence is better."
        )
        return await self.provider.complete([ChatMessage("system", system), ChatMessage("user", user)])
