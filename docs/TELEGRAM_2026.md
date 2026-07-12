# Telegram integration status

Haruka is an engine, so Telegram features live behind adapters and are never
silently enabled as product behavior.

## Bot API 10.1 (11 June 2026)

`BotAPIClient` supports generic calls plus typed convenience methods for:

- rich messages and streamed rich-message drafts;
- ordinary streamed message drafts;
- guest queries / guest mode;
- native checklists and checklist task replies;
- private-chat topics via pass-through `message_thread_id` options;
- deleting one or all reactions;
- media polls, one-option polls, member-only polls;
- business-message read/delete operations.

All wrappers accept extra keyword options. This preserves forward compatibility
with new fields without requiring an engine release.

## MTProto / Telethon

`TelegramEngine` remains the default user-session adapter for history, dialogs,
replies, files, stickers and reactions. Bot-only capabilities are not faked in
this adapter. A product can compose the MTProto adapter with `BotAPIClient`, or
replace both with TDLib.

Official references:
- https://core.telegram.org/bots/api-changelog
- https://core.telegram.org/bots/api
- https://core.telegram.org/api/layers
