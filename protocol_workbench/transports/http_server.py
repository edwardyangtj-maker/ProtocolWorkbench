from __future__ import annotations

import asyncio
import json
from typing import Optional

from aiohttp import web

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class HttpServerAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._app: web.Application | None = None
        self._reply_routes: list[dict] = []

    def add_reply_route(self, method: str, path: str, status: int, content_type: str, body: str):
        self._reply_routes.append({
            "method": method.upper(),
            "path": path,
            "status": status,
            "content_type": content_type,
            "body": body,
        })

    def clear_reply_routes(self):
        self._reply_routes.clear()

    async def start(self):
        try:
            self._app = web.Application()
            self._app.router.add_route("*", self.config.path, self._handle_request)
            self._app.router.add_route("*", self.config.path + "{tail:.*}", self._handle_request)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self.config.host, self.config.port)
            await self._site.start()
            self._set_state(self.STATE_LISTENING)
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"HTTP Server start failed: {e}")

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._site = None
        self._app = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        self.error_occurred.emit("HTTP Server cannot send proactively")
        return False

    async def _handle_request(self, request: web.Request) -> web.Response:
        try:
            body = await request.read()
            client_id = f"{request.remote}"
            self.data_received.emit(body, client_id)

            for route in self._reply_routes:
                if route["method"] == "*" or route["method"] == request.method:
                    req_path = request.path
                    if route["path"] == "*" or req_path == route["path"] or req_path.startswith(route["path"]):
                        return web.Response(
                            text=route["body"],
                            status=route["status"],
                            content_type=route["content_type"],
                        )

            return web.Response(text="OK", status=200)
        except Exception as e:
            self.error_occurred.emit(f"HTTP Server handle request error: {e}")
            return web.Response(text="Internal Error", status=500)
