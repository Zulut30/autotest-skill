# Telegram adapter decision

The first handler adapter supports aiogram 3, pinned in uv.lock. Local verification uses a real Dispatcher, Router and FSM storage with a recording Bot API transport. It does not contact Telegram and cannot establish live-client behavior.

Custom projects provide an explicitly authorized dispatcher factory and events with expected replies; repository imports require allow_project_commands. Tests of bot media/upload behavior are outside the first transport's scope and must block rather than invent successful results.

Live validation requires a genuine bot token and a dedicated test user's Telegram API ID, API hash and existing session through secure runtime bindings. Bot API cannot imitate the user. The live client uses Telethon; if a proxy-only cloud cannot route its protocol, use an authorized external runner. No session is created by guessing or by collecting credentials in chat.

Supported results keep commands, callbacks, FSM state, cross-user isolation and duplicate delivery separate. The fixture's in-memory deduplication is a bounded test behavior, not a production durability claim.

Saved fixture items have an ordinal ID plus user/chat ownership. `/item ID` allows the owner in the same chat or the fixture administrator; other users/chats are denied. Intentional defect mode bypasses role/ownership guards and shares FSM state. Local `expected_replies: [{chat_id: 501, text: Admin denied}]` binds a message to its recipient. Multi-chat reply assertions are rejected in live mode until that client capability is implemented and verified.
