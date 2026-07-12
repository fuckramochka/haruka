from __future__ import annotations

import logging
import random
from dataclasses import asdict
from datetime import datetime

from telethon.tl.custom import Message

from haruka.ai import AIEngine
from haruka.config.settings import Settings
from haruka.emotion import EmotionEngine
from haruka.memory import MemoryEngine
from haruka.goals import GoalEngine
from haruka.lore import LoreEngine
from haruka.persistence import Database
from haruka.persistence.json_store import JsonSnapshotStore
from haruka.personality import PersonalityEngine
from haruka.planning import PlanningEngine
from haruka.relationship import RelationshipEngine
from haruka.scheduler import Scheduler
from haruka.style import StyleLearningEngine
from haruka.telegram import TelegramEngine
from haruka.tools import ToolManager
from haruka.domain import IncomingMessage

logger = logging.getLogger(__name__)


class HarukaRuntime:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        telegram: TelegramEngine,
        memory: MemoryEngine,
        relationships: RelationshipEngine,
        goals: GoalEngine,
        lore: LoreEngine,
        style: StyleLearningEngine,
        emotion: EmotionEngine,
        planning: PlanningEngine,
        ai: AIEngine,
        snapshots: JsonSnapshotStore,
        scheduler: Scheduler,
        tools: ToolManager,
    ):
        self.settings = settings
        self.database = database
        self.telegram = telegram
        self.memory = memory
        self.relationships = relationships
        self.goals = goals
        self.lore = lore
        self.style = style
        self.emotion = emotion
        self.planning = planning
        self.ai = ai
        self.snapshots = snapshots
        self.scheduler = scheduler
        self.tools = tools
        self._known_chats: set[int] = set()

    @classmethod
    async def create(cls, settings: Settings) -> "HarukaRuntime":
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        database = Database(settings.db_path)
        await database.open()
        personality = PersonalityEngine(settings.name, settings.username)
        memory = MemoryEngine(database)
        emotion_state = await memory.self.load_emotion_state()
        goals = GoalEngine(database)
        await goals.ensure_defaults()
        return cls(
            settings=settings,
            database=database,
            telegram=TelegramEngine(settings),
            memory=memory,
            relationships=RelationshipEngine(database),
            goals=goals,
            lore=LoreEngine(database, settings.data_dir / "lore"),
            style=StyleLearningEngine(database),
            emotion=EmotionEngine(emotion_state),
            planning=PlanningEngine(),
            ai=AIEngine.from_settings(settings, personality),
            snapshots=JsonSnapshotStore(settings.snapshot_dir),
            scheduler=Scheduler(),
            tools=ToolManager(),
        )

    async def run_forever(self) -> None:
        await self.telegram.start(self.handle_message)
        self.scheduler.every(self.settings.snapshot_interval_seconds, self.snapshot_state, "snapshot-state")
        self.scheduler.every(self.settings.scan_interval_seconds, self.scan_memory, "scan-memory")
        self.scheduler.every(self.settings.style_refresh_interval_seconds, self.refresh_style_profiles, "refresh-style")
        if self.settings.initiative_enabled:
            self.scheduler.every(self.settings.initiative_interval_seconds, self.consider_initiative, "initiative")
        await self.telegram.run_forever()

    async def handle_message(self, message: IncomingMessage, raw_message: Message) -> None:
        await self._ensure_chat_profile(message.chat_id)

        observed_memory = await self.memory.observe(message)
        relationship = await self.relationships.observe(message)
        await self.goals.observe(message)
        lore = await self.lore.observe(message)
        emotion = self.emotion.observe(message)
        await self.memory.self.save_emotion_state(emotion)
        decision = self.planning.decide(message, emotion)
        logger.info(
            "message chat=%s sender=%s action=%s reason=%s",
            message.chat_id,
            message.sender_id,
            decision.action,
            decision.reason,
        )

        if decision.action == "react" and decision.reaction:
            await self.telegram.send_reaction(raw_message, decision.reaction)
            return
        if not decision.should_reply:
            return

        person = observed_memory.get("person") or {}
        self_notebook = await self.memory.self.load()
        world = await self.memory.world.get_chat(str(message.chat_id))
        style_profile = await self.style.get_profile(message.chat_id)
        recall_scope = "person" if message.sender_id is not None else "chat"
        recall_owner = str(message.sender_id) if message.sender_id is not None else str(message.chat_id)
        recalled = await self.memory.vector.search(recall_scope, recall_owner, message.text)
        active_goals = await self.goals.active_goals()
        relevant_lore = self.lore.choose_relevant(lore, message.text)
        reply = await self.ai.generate_reply(
            message=message,
            people_memory=person,
            self_memory=self_notebook,
            world_memory=world,
            style_profile=style_profile,
            emotion=emotion,
            recalled_memories=recalled,
            relationship=relationship,
            active_goals=active_goals,
            relevant_lore=relevant_lore,
            long=decision.action == "long_response",
        )
        if reply:
            await self.telegram.send_message(raw_message, reply)
            await self.memory.self.add_diary_entry(
                f"Talked with {message.sender_name or message.sender_id} in {message.chat_title or message.chat_id}: {reply[:240]}"
            )
            await self.memory.self.record_goal_progress(
                "build real relationships",
                f"Maintained continuity with {message.sender_name or message.sender_id}",
            )

    async def _ensure_chat_profile(self, chat_id: int) -> None:
        if chat_id in self._known_chats:
            return
        self._known_chats.add(chat_id)
        existing = await self.style.get_profile(chat_id)
        if existing and existing.sample_size >= 100:
            return
        try:
            texts = await self.telegram.load_recent_texts(chat_id, limit=500)
        except Exception:
            logger.exception("Could not load chat history for style profile: %s", chat_id)
            return
        await self.style.learn_from_texts(chat_id, texts)

    async def scan_memory(self) -> None:
        messages = await self.telegram.scan_recent_messages(limit_per_chat=5)
        for message in messages:
            if await self.memory.world.has_message(message.chat_id, message.message_id):
                continue
            await self._ensure_chat_profile(message.chat_id)
            await self.memory.observe(message)
            await self.relationships.observe(message)
            await self.goals.observe(message)
            await self.lore.observe(message)
            self.emotion.observe(message)
        await self.memory.self.save_emotion_state(self.emotion.state)

    async def refresh_style_profiles(self) -> None:
        for chat_id in list(self._known_chats):
            try:
                texts = await self.telegram.load_recent_texts(chat_id, limit=500)
            except Exception:
                logger.exception("Could not refresh chat style profile: %s", chat_id)
                continue
            await self.style.learn_from_texts(chat_id, texts)

    async def consider_initiative(self) -> None:
        if random.random() > self.settings.initiative_probability:
            return
        dialogs = await self.telegram.known_dialogs()
        if not dialogs:
            return
        chat_id, chat_title = random.choice(dialogs)
        await self._ensure_chat_profile(chat_id)
        style_profile = await self.style.get_profile(chat_id)
        self_notebook = await self.memory.self.load()
        world = await self.memory.world.get_chat(str(chat_id))
        lore = await self.lore.get(chat_id)
        active_goal = await self.goals.choose_initiative_goal()
        lore_seed = self.lore.choose_initiative_seed(lore)
        if not active_goal and not lore_seed:
            return
        reply = await self.ai.generate_initiative(
            chat_title=chat_title,
            self_memory=self_notebook,
            world_memory=world,
            style_profile=style_profile,
            emotion=self.emotion.state,
            active_goal=active_goal,
            lore_seed=lore_seed,
        )
        if not reply.strip():
            return
        await self.telegram.send_chat_message(chat_id, reply.strip())
        if active_goal:
            await self.goals.advance(active_goal.title, 1.0, "acted on initiative")
        await self.memory.self.add_diary_entry(
            f"Wrote first in {chat_title or chat_id}: {reply[:240]}"
        )

    async def close(self) -> None:
        await self.scheduler.stop()
        await self.telegram.close()
        await self.database.close()

    async def snapshot_state(self) -> None:
        notebook = await self.memory.self.load()
        await self.memory.self.save_emotion_state(self.emotion.state)
        await self.snapshots.write(
            "self_memory",
            {
                "self": notebook,
                "emotion": self._jsonable(asdict(self.emotion.state)),
            },
        )

    def _jsonable(self, value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        return value
