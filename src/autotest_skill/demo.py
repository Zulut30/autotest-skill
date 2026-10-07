"""Isolated demonstration target. Never deploy this fixture as a production service."""

import json
import secrets
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class State:
    def __init__(self, defects=False):
        self.lock = threading.RLock()
        self.defects = defects
        self.reset()

    def reset(self):
        with self.lock:
            self.sessions = {}
            self.items = {1: {"id": 1, "owner": "alice", "name": "Alice item", "quantity": 1},
                          2: {"id": 2, "owner": "bob", "name": "Bob item", "quantity": 1}}
            self.next_id = 3
            self.idempotency = {}
            self.dependency_down = False


def handler_for(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, body=None, content_type="application/json"):
            content = b"" if body is None else (json.dumps(body).encode() if content_type == "application/json" else body.encode())
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def identity(self):
            return state.sessions.get(self.headers.get("Authorization", "").removeprefix("Bearer "))

        def body(self):
            length = int(self.headers.get("Content-Length", 0))
            if length > 1_000_000:
                raise ValueError("oversized")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("object required")
            return value

        def do_GET(self):
            path = urlsplit(self.path).path
            with state.lock:
                if path == "/health":
                    return self.respond(200, {"ready": True, "fixture": True})
                if path == "/api/dependent":
                    return self.respond(503 if state.dependency_down else 200, {"available": not state.dependency_down})
                if path == "/openapi.json":
                    return self.respond(200, openapi())
                if path == "/":
                    from pathlib import Path
                    page = Path(__file__).parent / "assets" / "demo.html"
                    if page.is_file():
                        return self.respond(200, page.read_text().replace("__DEFECTS__", str(state.defects).lower()), "text/html; charset=utf-8")
                    return self.respond(200, {"fixture": True, "ready": True})
                user = self.identity()
                if not user:
                    return self.respond(401, {"error": "unauthorized"})
                if path == "/api/me":
                    return self.respond(200, {"username": user, "role": "admin" if user == "admin" else "user"})
                if path == "/api/items":
                    return self.respond(200, {"items": [item for item in state.items.values() if item["owner"] == user]})
                if path.startswith("/api/items/"):
                    try:
                        item = state.items[int(path.rsplit("/", 1)[1])]
                    except (KeyError, ValueError):
                        return self.respond(404, {"error": "not found"})
                    if item["owner"] != user and user != "admin" and not state.defects:
                        return self.respond(403, {"error": "forbidden"})
                    return self.respond(200, item)
                return self.respond(404, {"error": "not found"})

        def do_POST(self):
            path = urlsplit(self.path).path
            try:
                body = self.body()
            except (ValueError, TypeError, json.JSONDecodeError):
                return self.respond(400, {"error": "invalid body"})
            with state.lock:
                if path == "/api/login":
                    user = body.get("username")
                    if user not in {"alice", "bob", "admin"} or body.get("password") != "demo-password":
                        return self.respond(401, {"error": "invalid credentials"})
                    token = secrets.token_urlsafe(24)
                    state.sessions[token] = user
                    return self.respond(200, {"authorization": "Bearer " + token, "username": user})
                user = self.identity()
                if not user:
                    return self.respond(401, {"error": "unauthorized"})
                if path == "/api/logout":
                    state.sessions.pop(self.headers.get("Authorization", "").removeprefix("Bearer "), None)
                    return self.respond(204)
                if path.startswith("/__test/"):
                    if user != "admin":
                        return self.respond(403, {"error": "forbidden"})
                    if path == "/__test/reset":
                        state.reset()
                        return self.respond(200, {"reset": True})
                    if path == "/__test/dependency":
                        state.dependency_down = body.get("down") is True
                        return self.respond(200, {"down": state.dependency_down})
                if path == "/api/items":
                    name, quantity = body.get("name"), body.get("quantity")
                    if not isinstance(name, str) or not name.strip() or len(name) > 100 or type(quantity) is not int or not 1 <= quantity <= 100:
                        return self.respond(422, {"error": "invalid item"})
                    key = self.headers.get("Idempotency-Key")
                    if key and (user, key) in state.idempotency:
                        return self.respond(200, state.idempotency[(user, key)])
                    item = {"id": state.next_id, "owner": user, "name": name, "quantity": quantity}
                    state.next_id += 1
                    state.items[item["id"]] = item
                    if key:
                        state.idempotency[(user, key)] = item
                    return self.respond(201, item)
                return self.respond(404, {"error": "not found"})
    return Handler


def openapi():
    return {"openapi": "3.0.3", "info": {"title": "Autotest fixture", "version": "1"}, "paths": {
        "/health": {"get": {"responses": {"200": {"description": "ready", "content": {"application/json": {
            "schema": {"type": "object", "required": ["ready"], "properties": {"ready": {"type": "boolean"}}}}}}}}}}}


@contextmanager
def start_demo(defects=False, port=0):
    state = State(defects)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def execute(args):
    state = State(args.defects)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(state))
    print(f"Isolated demo listening on 127.0.0.1:{args.port}; defects={args.defects}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
