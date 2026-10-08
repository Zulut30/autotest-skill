# Access-control experiments

Each negative oracle is executed against a clean control and a deliberately broken owned fixture. A failure on the broken fixture is the expected detector result; it is not an unexplained mandatory test failure. Independent checks continue after a failing oracle.

| Target | Role oracle | Ownership oracle | Transport |
| --- | --- | --- | --- |
| API | Alice receives 403 from the admin endpoint; admin is allowed | Alice receives 403 for Bob's item; owner/admin are allowed | Real loopback HTTP |
| Telegram | Ordinary user receives Admin denied; fixture admin is allowed | Another user/chat cannot read a saved item or inherit its dialog state | Real aiogram dispatcher/FSM, recording outbound transport |
| Android | Alice sees Admin denied after a real backend request | Alice sees Foreign item denied after requesting Bob's object | Actual signed APK, Appium/UiAutomator2 and loopback backend |

Reports retain declared requirements, expected/observed responses and paired run identities. Synthetic role and ownership bypasses only exist in explicitly enabled defect mode. The portable five-case corpus remains separate from these expanded access experiments and optional native runs. No generic vulnerability recall is inferred from these cases.

The local bot result establishes handler behavior. Live Telegram delivery is a separate release gate. Current Android versions, other platforms and arbitrary application protocols need their own runner and domain oracles.
