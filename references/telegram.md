# Telegram checks

Use `examples/telegram.yaml` for actual aiogram dispatcher/FSM handler checks with recording transport. It exercises start/help/unknown commands, dialogs, invalid input, cancel/inline callbacks, isolation and duplicates. Webhook tests authenticate the HTTP header and enter aiogram's real webhook handler; their calls still do not prove real Telegram delivery.

For a dedicated owned bot, `examples/telegram-live.yaml` uses Telethon with a preauthorized test-user StringSession and the bot token from secure environment settings. No interactive login or on-disk session is allowed. An existing webhook blocks fixture polling instead of being overwritten. Test-user identity filters prevent replies to others. Missing credentials, protocol connectivity or a second user for live isolation remain blocked prerequisites. Scope and incomplete wire-request counters are explicit.

Do not ask users to paste credentials into chat or configuration. Do not broadcast, send to unrelated contacts or read unrelated chats. A live result requires actual matching replies through the configured owned bot.
