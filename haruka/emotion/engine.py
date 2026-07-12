from __future__ import annotations

import random

from haruka.domain import EmotionState, IncomingMessage, utc_now


class EmotionEngine:
    def __init__(self, state: EmotionState | None = None):
        self.state = state or EmotionState()

    def observe(self, message: IncomingMessage) -> EmotionState:
        text = message.text.lower()
        self.state.updated_at = utc_now()
        self.state.energy = max(0.1, self.state.energy - 0.003)
        self.state.curiosity = min(1.0, self.state.curiosity + (0.02 if "?" in text else -0.002))
        if any(word in text for word in ("спасибо", "thanks", "круто", "nice")):
            self.state.mood = "warm"
            self.state.trust = min(1.0, self.state.trust + 0.01)
        elif any(word in text for word in ("ненавижу", "stupid", "туп", "идиот")):
            self.state.mood = "guarded"
            self.state.trust = max(0.0, self.state.trust - 0.02)
        elif random.random() < 0.02:
            self.state.mood = random.choice(["quiet", "curious", "neutral", "playful"])
        return self.state
