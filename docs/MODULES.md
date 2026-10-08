# Configure modules

Every check declares its requirement, oracle, severity/impact, profiles and dependencies. Use `validate` before execution. Missing prerequisites block only dependent checks. Existing repository commands require `allow_project_commands`; commands are argv, not interpolated shell text. Interactive or mutating checks require `allow_mutations` and `mutating`.

| Module | Configuration and actual setup | Limits |
| --- | --- | --- |
| API | `kind: http`, exact `allowed_origins`, expected status/JSON/headers, local `openapi_file`; env/capture-backed authorization | No redirect authority expansion; bounded bodies; local OpenAPI refs only |
| Web | `kind: web`, semantic role/label/test-id actions; install Chromium, then doctor browser probe | No blind form submissions, sockets or approved-baseline updates; timings are lab values |
| Local Telegram | `kind: telegram`, scenario or explicit events/replies; install telegram extra | Real aiogram framework, recording transport; no live-user proof |
| Live Telegram | `mode: live`, own dedicated bot and preauthorized `TG_SESSION`, `TG_API_ID`, `TG_API_HASH`, `TG_BOT_TOKEN` in secure environment settings | No interactive login, stored session files or takeover of existing webhook; actual credentials absent here |
| Android | `kind: android`, explicit `udid`, server origin, package/activity/APK and assertions; isolated runner | API26 fixture validated. iOS/desktop unsupported; declare reset/mutations and authorize device-wide network controls |
| Performance | `kind: performance`, k6 or builtin, warm-up, requests/concurrency, p95/error-rate and compatible baseline | Bounded synthetic workload; duplicate experiment required for regression claim |
| Security | `kind: security`, source path/simple Python pins/local rules/declared response headers | Potential issues with scope/applicability; no full security guarantee |

For Android use `AUTOTEST_TOOLS_DIR` and `scripts/setup_android.py`, then `scripts/start_android.sh`. Bootstrap archives are SHA256 pinned from the initially verified official archive; SDK manager and npm keep their ordinary verification. SDK packages may advance upstream; their actual source.properties versions must be reviewed against the recorded reference. The script never overwrites an existing AVD descriptor. Build the fixture with `ANDROID_HOME=... scripts/build_android.sh`. Enable genuine native tests with `AUTOTEST_RUN_ANDROID=1` only on that dedicated runner.

The isolated Semgrep environment installs pinned transitive dependencies from `scripts/security-tools.lock` via `scripts/setup_security.sh`. Set `AUTOTEST_SEMGREP_BINARY` for its executable. pip-audit is in the security Python extra. k6 v1.0.0 and Gitleaks v8.24.3 can be installed from verified upstream releases or `go install go.k6.io/k6@v1.0.0` and `go install github.com/zricethezav/gitleaks/v8@v8.24.3` with Go module checksums enabled. Set `AUTOTEST_K6_BINARY` and `AUTOTEST_GITLEAKS_BINARY` if they are outside PATH. This cloud used verified Go1.27.1; `/usr/bin/go` on some images is a board game and must not be mistaken for the compiler.

Detailed workflow references: [backend](../references/backend.md), [web](../references/web.md), [security](../references/security.md), [native runner](NATIVE-RUNNER.md). Version inputs are recorded in [tool versions](../scripts/tool-versions.json). Main Python dependencies are pinned in uv.lock. No credential values belong in config, reports or Git.
