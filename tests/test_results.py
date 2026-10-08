from autotest_skill.results import CheckResult, RunReport


def report(*statuses):
    return RunReport(
        run_id="run",
        project="test",
        profile="smoke",
        tool_version="test",
        started_at="now",
        config_digest="test",
        results=[
            CheckResult(id=str(i), kind="http", status=s, oracle="expected", requirement="test")
            for i, s in enumerate(statuses)
        ],
    )


def test_partial_or_zero_checks_do_not_become_green():
    assert report().exit_code() == 2
    assert report("skipped").exit_code() == 2
    assert report("observation").exit_code() == 2
    assert report("passed", "blocked").exit_code() == 2
    assert report("passed", "error").exit_code() == 3
    assert report("passed", "failed").exit_code() == 1
    assert report("passed").exit_code() == 0


def test_retry_does_not_hide_flakiness():
    r = report("passed")
    r.results[0].flaky = True
    assert r.exit_code() == 1
