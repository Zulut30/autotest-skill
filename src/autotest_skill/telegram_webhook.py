"""HTTP ingress fixture uses the real aiogram webhook entrypoint and a protected route."""

import asyncio
import hmac
import json
import secrets
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from aiogram import Bot
from .telegram_demo import create_dispatcher
from .telegram_transport import RecordingSession


@contextmanager
def start_webhook():
    session=RecordingSession()
    bot=Bot(token=f"{123456789}:{'A'*35}",session=session)
    dispatcher=create_dispatcher()
    loop=asyncio.new_event_loop()
    worker=threading.Thread(target=loop.run_forever,daemon=True);worker.start()
    shared=secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_args):pass
        def do_POST(self):
            if self.path!='/webhook':
                self.send_response(404);self.end_headers();return
            received=self.headers.get('X-Telegram-Bot-Api-Secret-Token','')
            if not hmac.compare_digest(received,shared):
                self.send_response(403);self.end_headers();return
            length=int(self.headers.get('Content-Length',0))
            if length>1_000_000:
                self.send_response(413);self.end_headers();return
            try:
                update=json.loads(self.rfile.read(length))
                future=asyncio.run_coroutine_threadsafe(dispatcher.feed_webhook_update(bot,update,_timeout=5),loop)
                future.result(timeout=10)
            except Exception:
                self.send_response(500);self.end_headers();return
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(b'{"ok":true}')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    serving=threading.Thread(target=server.serve_forever,daemon=True);serving.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}',shared,dispatcher,session,bot
    finally:
        server.shutdown();server.server_close();serving.join()
        async def close():
            await dispatcher.storage.close();await session.close()
        asyncio.run_coroutine_threadsafe(close(),loop).result(timeout=5)
        loop.call_soon_threadsafe(loop.stop);worker.join();loop.close()
