import json
from autotest_skill.discovery import discover


def test_discovery_finds_scripts_without_executing_or_reading_secrets(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "echo would-execute"}}))
    (tmp_path / ".env").write_text("TOKEN=must-not-be-read")
    (tmp_path / "sample.test.js").write_text("test source")
    result = discover(tmp_path)
    assert result["candidate_commands"][0]["argv"] == ["npm", "run", "test"]
    assert "sample.test.js" in result["test_files"]
    assert "must-not-be-read" not in json.dumps(result)
