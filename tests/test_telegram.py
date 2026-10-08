from autotest_skill.config import Config
from autotest_skill.runner import run_config


def bot_config(scenario="start", **spec):
    return Config.model_validate(
        {
            "project": "bot",
            "allow_mutations": spec.get("mode") == "live",
            "checks": [
                {
                    "id": "bot.scenario",
                    "kind": "telegram",
                    "mutating": spec.get("mode") == "live",
                    "requirement": "TG-DIALOG",
                    "oracle": "Bot scenario matches documented replies, state and effects",
                    "spec": {"scenario": scenario, **spec},
                }
            ],
        }
    )


def test_start_help_and_unknown_commands_use_real_handlers(tmp_path):
    report, _ = run_config(bot_config(), tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0
    assert report.results[0].actual["events_executed"] == 3
    assert report.results[0].actual["live_telegram_validated"] is False
    assert report.results[0].actual["mode"] == "local_recording_transport"


def test_buttons_callback_ack_tampering_and_stale_confirmation(tmp_path):
    report, _ = run_config(bot_config("callback"), tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0
    actual = report.results[0].actual
    buttons = [button for call in actual["calls"] for button in call.get("buttons", [])]
    assert {"text": "Confirm", "data": "confirm"} in buttons
    assert {"text": "Cancel", "data": "cancel"} in buttons
    answers = [call for call in actual["calls"] if call["method"] == "answerCallbackQuery"]
    assert len(answers) == 3
    assert len(actual["items"]) == 1
    assert actual["states"]["user_a"] is None


def test_conversation_completion_invalid_input_and_cancel(tmp_path):
    for scenario in ("dialog", "invalid", "cancel"):
        report, _ = run_config(bot_config(scenario), tmp_path, tmp_path / "runs")
        assert report.exit_code() == 0, scenario
    events = [{"text": "/new"}, {"text": "x" * 101}]
    report, _ = run_config(bot_config("invalid", events=events), tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0
    assert report.results[0].actual["states"]["user_a"] == "Collect:name"


def test_user_chat_isolation_and_seeded_storage_leak(tmp_path):
    clean, _ = run_config(bot_config("isolation"), tmp_path, tmp_path / "runs")
    assert clean.exit_code() == 0
    broken, _ = run_config(bot_config("isolation", defects=True), tmp_path, tmp_path / "runs")
    assert broken.results[0].status == "failed"
    assert broken.results[0].actual["states"]["user_b"] is not None


def test_admin_command_denies_normal_user_and_allows_admin(tmp_path):
    config = bot_config(
        events=[{"text": "/admin", "user_id": 501}, {"text": "/admin", "user_id": 9001}],
        expected_messages=["Admin denied", "Admin allowed"],
    )
    report, _ = run_config(config, tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0


def test_duplicate_delivery_has_one_effect(tmp_path):
    report, _ = run_config(bot_config("duplicate"), tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0
    assert len(report.results[0].actual["items"]) == 1
    report, _ = run_config(bot_config("delivery"), tmp_path, tmp_path / "runs")
    assert report.exit_code() == 0
    assert report.results[0].actual["delivery_entrypoint"] == "feed_webhook_update"


def test_real_webhook_http_ingress_authenticates_and_deduplicates():
    import httpx

    from autotest_skill.telegram_transport import update_event
    from autotest_skill.telegram_webhook import start_webhook

    with (
        start_webhook() as (base, shared, _dispatcher, session, bot),
        httpx.Client(base_url=base) as client,
    ):
        payload = update_event(bot, 1, text="/start").model_dump(mode="json", exclude_none=True)
        assert client.post("/webhook", json=payload).status_code == 403
        headers = {"X-Telegram-Bot-Api-Secret-Token": shared}
        assert client.post("/webhook", json=payload, headers=headers).json()["ok"] is True
        assert client.post("/webhook", json=payload, headers=headers).status_code == 200
        assert len(session.calls) == 1


def test_missing_live_credentials_block_without_claiming_validation(tmp_path, monkeypatch):
    for name in ("TG_BOT_TOKEN", "TG_API_ID", "TG_API_HASH", "TG_SESSION"):
        monkeypatch.delenv(name, raising=False)
    report, _ = run_config(
        bot_config("dialog", mode="live", serve_fixture=True), tmp_path, tmp_path / "runs"
    )
    assert report.results[0].status == "blocked"
    assert "TG_BOT_TOKEN" in report.results[0].reason
    assert report.exit_code() == 2
