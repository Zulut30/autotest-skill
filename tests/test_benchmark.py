from autotest_skill.benchmark import score


def test_benchmark_keeps_blocked_cases_in_the_denominator():
    rows = [
        {
            "id": "found",
            "severity": "critical",
            "broken_status": "failed",
            "clean_status": "passed",
        },
        {
            "id": "blocked",
            "severity": "critical",
            "broken_status": "blocked",
            "clean_status": "passed",
        },
        {
            "id": "false-positive",
            "severity": "high",
            "broken_status": "failed",
            "clean_status": "failed",
        },
    ]
    measured = score(rows)
    assert measured["known_defects"] == 3 and measured["detected"] == 2
    assert measured["missed"] == ["blocked"]
    assert measured["critical_detected"] == 1 and measured["critical_known"] == 2
    assert measured["critical_high_false_positives"] == 1
    assert measured["incomplete_pairs"] == 1 and not measured["mandatory_benchmark_gates_passed"]
    assert not score([])["all_pairs_passed"]
