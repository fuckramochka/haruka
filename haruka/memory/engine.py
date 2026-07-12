from __future__ import annotations

from typing import Any

from haruka.domain import IncomingMessage
from haruka.memory.people import PeopleMemory
from haruka.memory.self_memory import SelfMemory
from haruka.memory.vector import VectorMemory
from haruka.memory.world import WorldMemory
from haruka.persistence.database import Database


class MemoryEngine:
    def __init__(self, database: Database):
        self.people = PeopleMemory(database)
        self.self = SelfMemory(database)
        self.world = WorldMemory(database)
        self.vector = VectorMemory(database)

    async def observe(self, message: IncomingMessage) -> dict[str, Any]:
        person_profile = await self.people.observe_message(message)
        await self.world.observe_message(message)
        await self.vector.add(
            scope="chat",
            owner_id=str(message.chat_id),
            text=message.text,
            metadata={
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
            },
        )
        if message.sender_id is not None:
            await self.vector.add(
                scope="person",
                owner_id=str(message.sender_id),
                text=message.text,
                metadata={"chat_id": message.chat_id, "message_id": message.message_id},
            )
        return {"person": person_profile}
