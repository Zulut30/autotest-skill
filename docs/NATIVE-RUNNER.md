# Validated native runner

The executed reference uses Android 8.0.0/API26 **default x86** system image r1, emulator 37.2.12 build 16428233, platform-tools 37.0.1, Appium 3.1.0 and UiAutomator2 driver 8.7.0/server 10.6.6. Build uses platform API30 and build-tools 35.0.0; the signed fixture APK supports min API26. The cloud host provides 5 vCPUs/32 GiB. AVD uses two virtual cores, 1536 MiB, 480×800 at 160 dpi and SwiftShader. No /dev/kvm is available here.

Official Android archives were checked against Google's repository metadata, SDK installation retained its checksum verification, npm retained integrity checks, and Android Package Manager verified APK signatures. Do not disable these checks. Command-line tools 23 avdmanager failed to create the API26 descriptor in this environment; the small documented AVD descriptor in the start script was used and actually booted.

Set `AUTOTEST_TOOLS_DIR=/workspace/.autotest-tools` in this cloud environment, or install tools under `.autotest/tools` elsewhere. `scripts/start_android.sh` starts only a missing owned emulator/Appium instance and waits for boot. `scripts/build_android.sh` compiles and verifies the demo APK. Existing connected device `emulator-5554` is explicit; host Appium binds 127.0.0.1:4723. Runtime HTTP readiness is distinct from the successful semantic native title assertion retained in [native evidence](evidence/native-probe.json).

API30 Google APIs x86_64 software emulation booted but produced system ANRs and package-install timeouts. Those attempts were blocked and do not establish API30 workflow support. The API26 fixture is a bounded initial compatibility result; current Android versions and arbitrary apps need their own validated runner/device.

Do not use a personal device. Mutating checks require both configuration authorization and check declaration. Network changes require `allow_device_controls: true`. Secret-bound actions suppress screenshots. Logs and data stay under ignored `.autotest` directories.
