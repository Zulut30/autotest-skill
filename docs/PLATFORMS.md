# Platform and runner matrix

| Target | Initial adapter | Runtime | Validation status |
|---|---|---|---|
| API | HTTPX | Python 3.12+ | Pending implementation |
| Web | Playwright Chromium | Linux/macOS/Windows with browser dependencies | Pending implementation |
| Telegram logic | aiogram | Python, no Telegram credentials required | Pending implementation |
| Telegram live | Telethon | Isolated bot and test-user session; Telegram network access | Blocked until credentials supplied |
| Android | Appium UiAutomator2 | Android emulator/device and Appium server | Pending runner availability |
| iOS | Future adapter | macOS/device runner | Unsupported |
| Desktop | Future adapter | Platform-specific runner | Unsupported |

Support is earned by execution. This table is updated with evidence; writing an adapter alone does not establish platform readiness.
