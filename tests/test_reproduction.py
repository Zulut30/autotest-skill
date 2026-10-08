import hashlib
import json
import zipfile

from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config


def test_package_references_current_evidence_and_removes_credentials(tmp_path):
    with start_demo() as (base, _):
        config = Config.model_validate(
            {
                "project": "repro",
                "allowed_origins": [base],
                "allow_mutations": True,
                "checks": [
                    {
                        "id": "login",
                        "kind": "http",
                        "mutating": True,
                        "requirement": "AUTH",
                        "oracle": "Synthetic Alice session is created",
                        "spec": {
                            "base_url": base,
                            "method": "POST",
                            "path": "/api/login",
                            "json_body": {"username": "alice", "password": "demo-password"},
                            "capture": {"auth": "authorization"},
                        },
                    }
                ],
            }
        )
        report, folder = run_config(config, tmp_path, tmp_path / "runs")
        assert report.exit_code() == 0
        document = json.loads((folder / "reproduction.json").read_text())
        assert document["run_id"] == report.run_id
        for evidence in document["evidence"]:
            assert (
                evidence["sha256"]
                == hashlib.sha256((folder / evidence["path"]).read_bytes()).hexdigest()
            )
        with zipfile.ZipFile(folder / "reproduction.zip") as archive:
            assert set(archive.namelist()) == {
                "result.json",
                "summary.json",
                "reproduction.json",
                "login.http.json",
            }
            for name in archive.namelist():
                assert b"demo-password" not in archive.read(name)
        assert (folder / "reproduction.zip").stat().st_mode & 0o777 == 0o600
