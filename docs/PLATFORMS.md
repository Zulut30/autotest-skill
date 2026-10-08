# Platform and runner matrix

| Target | Initial adapter | Runtime | Validation status |
|---|---|---|---|
| API | HTTPX | Python 3.12+ | Real executed fixtures; see docs/PROGRESS.md |
| Web | Playwright Chromium | Linux/macOS/Windows with browser dependencies | Real executed fixtures; see docs/PROGRESS.md |
| Telegram logic | aiogram | Python, no Telegram credentials required | Real executed fixtures; see docs/PROGRESS.md |
| Telegram live | Telethon | Isolated bot and test-user session; Telegram network access | Blocked until credentials supplied |
| Android | Appium UiAutomator2 | Android emulator/device and Appium server | Actual API26 native install/screen/navigation; advanced scenarios tracked in roadmap |
| iOS | Future adapter | macOS/device runner | Unsupported |
| Desktop | Future adapter | Platform-specific runner | Unsupported |

Support is earned by execution. This table is updated with evidence; writing an adapter alone does not establish platform readiness.
