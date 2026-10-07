# Native Android adapter contract

A declared Android target has an explicit Appium origin, device UDID, package/activity and optionally a project-relative APK. Installation and data reset apply only to the isolated configured test device. Unknown devices are not selected automatically.

Lifecycle: probe Appium and device → install/launch supported APK → execute semantic accessibility/resource/text selectors → verify visible state and backend effects → save private current-run artifacts → terminate the owned session.

Actions cover click, fill, text/visibility assertions, back navigation, background/foreground, restart and scoped connectivity changes. Commands consume the shared action/time budget. An unavailable Appium server, emulator or installable artifact is blocked. A violated UI oracle is failed; adapter implementation errors remain error.

Screenshots and logs support an agent's design/UX analysis. No complete native accessibility certification is claimed. Android is the first supported native platform; iOS and desktop remain unsupported.

Cloud runner: Android 11/API 30 x86_64, emulator 37.2.12.0, software acceleration, Appium 3.1.0 and UiAutomator2 8.7.0. Exact installed metadata and startup steps are recorded after runner validation. The emulator, ADB and Appium are processes that must restart in a new task.
