import os
import subprocess
from pathlib import Path

from . import helpers

pytestmark = helpers.pytestmark


def test_actual_apk_install_and_semantic_launch():
    sdk = Path(os.environ.get("ANDROID_HOME", "/workspace/.autotest-tools/android"))
    adb = [str(sdk / "platform-tools" / "adb"), "-s", "emulator-5554"]
    present = subprocess.run(
        [*adb, "shell", "pm", "path", "com.autotest.demo"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    if present.stdout.strip():
        subprocess.run(
            [*adb, "uninstall", "com.autotest.demo"], check=True, capture_output=True, timeout=60
        )
    report, folder = helpers.execute_native(
        65,
        [{"action": "expect_text", "text": "Autotest Demo"}],
        apk=".autotest/android-build/autotest-demo.apk",
    )
    assert report.results[0].actual["package"] == "com.autotest.demo"
    assert report.results[0].actual["platform_version"] == "8.0.0"
    assert (folder / "native.step-65.android.json").is_file()
