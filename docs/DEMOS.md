# Reproducible demonstrations

Use the source checkout and `scripts/install.sh`. Web uses real Chromium, Telegram uses actual aiogram handlers with recording transport, and Android uses the signed native fixture through Appium. Every mode creates fresh owned backend data. Synthetic names, accounts and intentional defects are isolated from production.

```bash
# Portable demonstrations; no Telegram credentials needed:
.venv/bin/python scripts/demo.py --module web --mode paired
.venv/bin/python scripts/demo.py --module telegram --mode paired

# Native reference prerequisites:
.venv/bin/python scripts/setup_android.py
bash scripts/start_android.sh
scripts/build_android.sh
.venv/bin/python scripts/demo.py --module android --mode paired --udid emulator-5554

# All three, with a new run directory for each invocation:
.venv/bin/python scripts/demo.py --module all --mode paired
```

In this cloud environment set `AUTOTEST_TOOLS_DIR=/workspace/.autotest-tools` before Android setup/start. Elsewhere the default is `.autotest/tools`. Do not share the emulator with another test job. Port 8765 must be free for the native host-loopback bridge; the script does not terminate unrelated listeners. The first Appium session installs its verified helper APKs automatically. `--reuse-runtime` is only for subsequent runs after that bootstrap.

`--mode clean` runs the corrected fixture; `--mode broken` enables its known defect. Web falsely acknowledges save without persistence; Telegram leaks FSM state between users/chats; Android falsely acknowledges save without POST. Paired mode executes the same oracle in both modes. It succeeds only when the clean control passes and the broken target produces the expected failed oracle. The underlying failed result remains failed in its report.

Read the printed current directory's `demo.json`, then each run's `report.md`, expected/observed values and `reproduction.zip`. Native output also records the actual backend item count. A missing tool stays blocked and prevents the demonstration gate from passing. An X screenshot cannot substitute for these runtime results.

For a genuine Telegram-client demo, securely supply the dedicated test bot and preauthorized user bindings described in [TELEGRAM-ADAPTER.md](TELEGRAM-ADAPTER.md), then run `examples/telegram-live.yaml`. This is prepared but unverified while those bindings and the protocol route are absent. The reproducible local handler demonstration does not close roadmap steps 59–60.
