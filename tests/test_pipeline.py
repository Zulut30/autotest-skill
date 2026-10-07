import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from autotest_skill.config import Config
from autotest_skill.runner import run_config


def test_http_plan_to_current_run_evidence_detects_real_mismatch(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers()
            self.wfile.write(b'{"ready":false}')
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        config = Config.model_validate({"project": "pipeline", "allowed_origins": [origin], "checks": [{
            "id": "ready", "kind": "http", "requirement": "API readiness", "oracle": "Health returns ready true",
            "spec": {"base_url": origin, "expected_json": {"ready": True}}}]})
        report, folder = run_config(config, tmp_path, tmp_path / "runs")
        assert report.exit_code() == 1
        assert report.results[0].status == "failed"
        assert len(report.results[0].attempts) == 2
        saved = json.loads((folder / "result.json").read_text())
        assert saved["run_id"] == report.run_id
        assert saved["results"][0]["actual"]["json"]["ready"] is False
        assert (folder / report.results[0].evidence[0]).is_file()
    finally:
        server.shutdown(); server.server_close(); thread.join()
