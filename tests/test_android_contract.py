import pytest
from pydantic import ValidationError

from autotest_skill.config import Config
from autotest_skill.runner import run_config


def test_missing_native_server_is_blocked_and_other_checks_can_continue(tmp_path):
    config = Config.model_validate(
        {
            "project": "native",
            "allowed_origins": ["http://127.0.0.1:1"],
            "checks": [
                {
                    "id": "native",
                    "kind": "android",
                    "requirement": "APP-SAVE",
                    "oracle": "Native app shows its saved state",
                    "spec": {
                        "server_url": "http://127.0.0.1:1",
                        "udid": "emulator-5554",
                        "package": "com.autotest.demo",
                        "activity": ".MainActivity",
                        "actions": [{"action": "expect_text", "text": "Autotest Demo"}],
                    },
                }
            ],
        }
    )
    report, _ = run_config(config, tmp_path, tmp_path / "runs")
    assert report.results[0].status == "blocked"
    assert report.exit_code() == 2


def test_native_rotation_requires_device_control_authorization():
    from tests.native.helpers import native_case

    config = native_case(
        "boundary",
        [
            {"action": "rotate", "orientation": "LANDSCAPE"},
            {"action": "expect_text", "text": "Autotest Demo"},
        ],
    ).model_dump()
    config["allow_device_controls"] = False
    with pytest.raises(ValidationError):
        Config.model_validate(config)


def test_fixture_controls_cannot_change_an_unrelated_application():
    from tests.native.helpers import native_case

    with pytest.raises(ValidationError):
        native_case(
            "boundary",
            [{"action": "expect_text", "text": "An unrelated app"}],
            package="com.acme.wallet",
            fixture_defects=True,
        )


def test_unimplemented_native_baseline_cannot_silently_pass(tmp_path):
    from tests.native.helpers import native_case

    config = native_case(
        "baseline", [{"action": "expect_text", "text": "Autotest Demo"}], baseline="baseline.png"
    )
    report, _ = run_config(config, tmp_path, tmp_path / "runs")
    assert report.exit_code() == 2
    assert "baselines are not supported" in report.results[0].reason
