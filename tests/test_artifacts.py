import json
import os

import pytest

from autotest_skill.artifacts import create_run, safe_file, write_json
from autotest_skill.secrets import Redactor


def test_unique_current_run_and_private_redacted_artifact(tmp_path):
    first, folder = create_run(tmp_path)
    second, _ = create_run(tmp_path)
    assert first != second
    file = write_json(folder, "result.json", {"token": "synthetic"}, Redactor())
    assert json.loads(file.read_text())["token"] == "[REDACTED]"
    assert os.stat(file).st_mode & 0o077 == 0
    assert os.stat(folder).st_mode & 0o077 == 0


def test_artifact_traversal_and_symlink_escape_rejected(tmp_path):
    _, folder = create_run(tmp_path)
    with pytest.raises(ValueError):
        safe_file(folder, "../outside.json")
    (folder / "outside").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        safe_file(folder, "outside/result.json")
