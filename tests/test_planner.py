from autotest_skill.config import Config
from autotest_skill.planner import select


def configuration():
    checks = []
    for name, profiles, deps in (
        ("login", ["release"], []),
        ("profile", ["smoke", "changed"], ["login"]),
        ("other", ["release", "changed"], []),
    ):
        checks.append(
            {
                "id": name,
                "kind": "http",
                "requirement": name,
                "oracle": "Expected behavior is observed",
                "profiles": profiles,
                "depends_on": deps,
                "spec": {"base_url": "http://localhost"},
            }
        )
    return Config.model_validate(
        {"project": "test", "allowed_origins": ["http://localhost"], "checks": checks}
    )


def test_prerequisites_are_ordered_even_outside_selected_profile():
    assert [c.id for c in select(configuration(), "smoke")] == ["login", "profile"]


def test_changed_selection_and_safe_fallback():
    config = configuration()
    config.checks[1].covers = ["src/profile/**"]
    config.checks[2].covers = ["src/other/**"]
    assert [c.id for c in select(config, "changed", ["src/other/view.py"])] == ["other"]
    assert [c.id for c in select(config, "changed", [])] == ["login", "profile"]
    assert [c.id for c in select(config, "changed", ["unknown.py"])] == ["login", "profile"]
