import json

from autotest_skill.config import Config
from autotest_skill.demo import openapi, start_demo
from autotest_skill.runner import run_config


def test_contract_detects_body_regression_despite_http_200(tmp_path):
    document = openapi()
    (tmp_path / "api.json").write_text(json.dumps(document))
    with start_demo() as (base, _):
        config = Config.model_validate(
            {
                "project": "contract",
                "allowed_origins": [base],
                "checks": [
                    {
                        "id": "contract",
                        "kind": "http",
                        "requirement": "API contract",
                        "oracle": "Response matches the declared ready schema",
                        "spec": {"base_url": base, "path": "/health", "openapi_file": "api.json"},
                    }
                ],
            }
        )
        report, _ = run_config(config, tmp_path, tmp_path / "runs")
        assert report.exit_code() == 0
        document["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["properties"]["ready"]["type"] = "string"
        (tmp_path / "api.json").write_text(json.dumps(document))
        report, _ = run_config(config, tmp_path, tmp_path / "runs")
        assert report.results[0].status == "failed"
