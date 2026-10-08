# Changelog

## Unreleased

- Web actions assert enabled/disabled/hidden state and preserve expected/observed assertion evidence, withholding sensitive text.
- Secret-bound web actions retain functional results while withholding screenshots; visual baseline checks still block when their image is unavailable.
- Demo saving guidance updates on login, logout and expired sessions; logout revokes the session and clears private UI data. Expired save attempts cannot reenable saving.
- `regression --from-run` proposes a pytest replay of a failed web scenario with reliable web/HTTP prerequisites. Preserves credential binding metadata, rejects redacted/sensitive inline inputs and unsupported result types, and refuses overwrites. The existing seeded mode remains available.

## 0.1.0a1 — alpha

Python CLI and packaged agent skill with strict configuration, bounded profiles, honest blocked/flaky outcomes, private current-run evidence and reproducible reports. Adapters cover real HTTP/OpenAPI, Playwright/Chromium/axe/visual baselines, actual aiogram handlers with recording transport, API26 Android/Appium, k6 and bounded security tools.

Executed five-case paired portable corpus, native save/reopen pairs, role/ownership experiments, lifecycle/transport/keyboard scenarios, isolated wheel installation and hosted CI. Demo projects and presentation assets are included in the repository.

Live Telegram transport and independent first-use validation remain incomplete release gates. iOS, desktop, native PNG baseline comparison and radio toggles on the reference runner remain unvalidated/unsupported as documented. The alpha is not published to PyPI or X.
