# Native Android checks

The reference runs a signed Java fixture through actual Appium/UiAutomator2 on Android 8.0/API26 x86. Use docs/NATIVE-RUNNER.md and examples/android.yaml. A PID or Appium /status response is not an app oracle; assert the screen and backend effect.

Require explicit device ID and exact Appium origin. APK paths remain under the project. Installing, clearing/resetting app state and interacting require declared mutation. Supplied APKs are force-installed to avoid stale same-version builds; signatures remain verified. Semantic locators must be unique. Text assertions wait for final state. Secret-bound/sensitive fills suppress screenshots.

Use controlled fixtures for incorrect credentials, expired sessions, roles, form boundaries, permission refusal, lifecycle, offline/recovery and save/reopen. Retain observed values, current APK fingerprint and run artifacts. Device-wide controls require separate authorization and isolated device use. Native baseline support must be validated before advertising it. Other Android versions need their own evidence; iOS/desktop remain future adapters.
