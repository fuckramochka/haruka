from __future__ import annotations

import random

from haruka.domain import ActionDecision, EmotionState, IncomingMessage


class PlanningEngine:
    def decide(self, message: IncomingMessage, emotion: EmotionState) -> ActionDecision:
        if not self._is_triggered(message):
            return self._ambient_decision(emotion)

        reply_bias = 0.75
        if emotion.energy < 0.35:
            reply_bias -= 0.25
        if emotion.mood in {"guarded", "quiet"}:
            reply_bias -= 0.15
        if random.random() > reply_bias:
            return ActionDecision("observe", "triggered but not socially necessary", False)

        long_chance = 0.08 if message.is_private else 0.025
        if random.random() < long_chance:
            return ActionDecision("long_response", "direct trigger with enough context", True)
        return ActionDecision("short_response", "direct trigger", True)

    def _ambient_decision(self, emotion: EmotionState) -> ActionDecision:
        roll = random.random()
        react_limit = 0.20 * emotion.energy
        short_limit = react_limit + 0.08 * emotion.motivation
        long_limit = short_limit + 0.02 * emotion.curiosity

        if roll < react_limit:
            return ActionDecision("react", "ambient human-like reaction", False, reaction=random.choice(["👍", "👀", "😂", "❤️", "🔥"]))
        if roll < short_limit:
            return ActionDecision("short_response", "rare ambient participation", True)
        if roll < long_limit:
            return ActionDecision("long_response", "rare thoughtful participation", True)
        return ActionDecision("observe", "default human-like observation", False)

    @staticmethod
    def _is_triggered(message: IncomingMessage) -> bool:
        return message.is_private or message.mentioned_haruka or message.is_reply_to_haruka

