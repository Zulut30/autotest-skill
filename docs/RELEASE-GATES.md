# Release gates

1. All supported modules have a real executed representative scenario. Live Telegram and Android remain required gates for the promised three-target release.
2. All critical seeded benchmark defects are detected and all clean controls produce zero confirmed critical/high false positives.
3. Five deterministic smoke runs agree on check statuses; unexplained mandatory-test failures or runner errors are absent.
4. Every confirmed finding includes its oracle, target version, reproduction and current-run evidence. Blocked, skipped and zero-test runs cannot become green success.
5. A clean installation executes the documented smoke command with pinned dependencies and verification enabled.
6. Secret handling and target/action boundaries pass adversarial tests.
7. A person uninvolved in development completes the quickstart and a 10–15 minute rehearsal demonstrates web, Telegram and Android without hidden manual steps.
8. Release metadata, license, source package and X materials describe only verified features. Publication to X is a separate user action unless explicitly requested.

The roadmap is a completion checklist. Documentation-only work does not close execution gates.
