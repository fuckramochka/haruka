# Haruka implementation plan

## Implemented foundation

- Async Telethon runtime
- Provider-abstracted AI client
- SQLite persistence repositories
- JSON snapshot export
- Three memory systems: people, self, world
- Emotion, personality, style, planning, scheduler engines
- Lightweight deterministic vector memory for semantic recall
- Relationship Engine with trust/friendship/interest/respect/attachment
- Goal Engine with active goals, priority, status, and progress
- Lore Engine with per-chat JSON lore snapshots
- Initiative loop for occasional first messages
- Recency-weighted recall so newer facts usually win while old recurring lore can resurface

## Requirement status

| Requirement | Status | Implementation |
| --- | --- | --- |
| Analyze last 500 messages | Implemented | `TelegramEngine.load_recent_texts(..., limit=500)` feeds `StyleLearningEngine.learn_from_texts` when Haruka first sees a chat and during refresh. |
| Trigger on name | Implemented | `TelegramEngine._to_incoming` sets `mentioned_haruka` when the configured display name appears. |
| Trigger on username | Implemented | `TelegramEngine._to_incoming` checks `@HARUKA_USERNAME`. |
| Trigger on reply | Implemented | `TelegramEngine._to_incoming` resolves replied message sender and checks Haruka's account id. |
| Scan every 10 seconds | Implemented | `HarukaRuntime.run_forever` schedules `scan_memory` with `HARUKA_SCAN_INTERVAL_SECONDS`. |
| User trust system | Basic implemented | `PeopleMemory` stores `trust_level` and adjusts relationship signals over time. |
| Autonomous diary | Implemented | `SelfMemory.add_diary_entry` records interactions in persistent self memory. |
| Goals system | Basic implemented | `SelfMemory` stores goals/current projects and `record_goal_progress` records progress. |
| Persist emotions across restarts | Implemented | `SelfMemory.load_emotion_state` and `save_emotion_state` store emotion in SQLite. |
| Auto-update Chat Style Profile | Implemented | `refresh_style_profiles` reloads the latest 500 messages for known chats on the scheduler. |
| Relationship Engine | Implemented | `RelationshipEngine` stores multi-dimensional user relationships in SQLite. |
| Goal Engine | Implemented | `GoalEngine` stores active goals with progress, status, and priority. |
| Lore Engine | Implemented | `LoreEngine` stores chat memes, inside jokes, events, and conflicts in SQLite and `data/lore/{chat_id}.json`. |
| Initiative | Implemented | `consider_initiative` periodically lets Haruka write first from a goal or lore seed. |
| New facts outweigh old facts | Implemented | Vector and lore recall both include recency weighting, while frequent/contextual old lore can still surface. |

## Next production hardening

- Replace lightweight vector embeddings with a real embedding provider.
- Add admin commands for memory inspection and correction.
- Add rate limits per chat and per user.
- Add sticker/photo/file selection policies.
- Add moderation and red-line rules per deployment context.
- Add automated integration tests with mocked Telethon events.
- Add configurable quiet hours and per-chat initiative permissions.
- Make relationship and lore extraction model-assisted instead of purely heuristic.
- Add admin commands to inspect/edit relationships, goals, and lore.
