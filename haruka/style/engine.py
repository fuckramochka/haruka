from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime

from haruka.domain import ChatStyleProfile
from haruka.persistence.database import Database

EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
WORD_RE = re.compile(r"[\wа-яА-ЯёЁ#@]{3,}", flags=re.UNICODE)


class StyleLearningEngine:
    def __init__(self, database: Database):
        self.database = database

    async def get_profile(self, chat_id: int) -> ChatStyleProfile | None:
        db = self.database.require()
        cursor = await db.execute(
            "SELECT data_json FROM chat_style_profiles WHERE chat_id = ?",
            (str(chat_id),),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        data = json.loads(row["data_json"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return ChatStyleProfile(chat_id=chat_id, **{k: v for k, v in data.items() if k != "chat_id"})

    async def learn_from_texts(self, chat_id: int, texts: list[str]) -> ChatStyleProfile:
        clean = [text.strip() for text in texts if text and text.strip()]
        word_counts: Counter[str] = Counter()
        punctuation = Counter()
        emoji_count = 0
        total_length = 0

        for text in clean:
            total_length += len(text)
            emoji_count += len(EMOJI_RE.findall(text))
            punctuation.update(char for char in text if char in "!?.,…)")
            word_counts.update(word.lower() for word in WORD_RE.findall(text))

        common_words = [word for word, _ in word_counts.most_common(50)]
        slang = [word for word in common_words if word.startswith("#") or word in {"лол", "кек", "имба", "жиза", "рофл"}]
        memes = [text[:120] for text in clean if any(marker in text.lower() for marker in ("ахах", "лол", "мем", "жиза"))][:30]

        profile = ChatStyleProfile(
            chat_id=chat_id,
            vocabulary=common_words,
            slang=slang,
            avg_message_length=(total_length / len(clean)) if clean else 0.0,
            emoji_rate=(emoji_count / len(clean)) if clean else 0.0,
            punctuation=dict(punctuation.most_common()),
            local_memes=memes,
            recurring_jokes=memes[:10],
            sample_size=len(clean),
            updated_at=datetime.now(UTC),
        )
        await self.save_profile(profile)
        return profile

    async def save_profile(self, profile: ChatStyleProfile) -> None:
        db = self.database.require()
        data = {
            "vocabulary": profile.vocabulary,
            "slang": profile.slang,
            "avg_message_length": profile.avg_message_length,
            "emoji_rate": profile.emoji_rate,
            "punctuation": profile.punctuation,
            "local_memes": profile.local_memes,
            "recurring_jokes": profile.recurring_jokes,
            "sample_size": profile.sample_size,
            "updated_at": profile.updated_at.isoformat(),
        }
        await db.execute(
            """
            INSERT INTO chat_style_profiles(chat_id, data_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (str(profile.chat_id), json.dumps(data, ensure_ascii=False), profile.updated_at.isoformat()),
        )
        await db.commit()
