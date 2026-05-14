from __future__ import annotations

import asyncio
import json
from typing import Optional

import aiohttp

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class HttpClientAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._session: aiohttp.ClientSession | None = None
        self._method = "POST"
        self._custom_headers: dict[str, str] = {}

    def set_method(self, method: str):
        self._method = method.upper()

    def set_custom_headers(self, headers: dict[str, str]):
        self._custom_headers = headers

    async def start(self):
        try:
            timeout = aiohttp.ClientTimeout(
                total=self.config.read_timeout_ms / 1000.0,
                connect=self.config.connect_timeout_ms / 1000.0,
            )
            
            # 配置TCP连接器，绑定本地IP和端口（如果配置了）
            connector = None
            if self.config.host and self.config.port:
                connector = aiohttp.TCPConnector(
                    local_addr=(self.config.host, self.config.port)
                )
            
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            self._set_state(self.STATE_CONNECTED)
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"HTTP Client start failed: {e}")

    async def stop(self):
        if self._session:
            await self._session.close()
            self._session = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._session:
            self.error_occurred.emit("HTTP Client not started")
            return False
        try:
            url = target if target else f"http://{self.config.remote_host}:{self.config.remote_port}{self.config.path}"
            content_type = "application/json" if self.config.payload_type.value == "json" else "text/plain"
            headers = {"Content-Type": content_type}
            headers.update(self._custom_headers)

            method = self._method
            if method in ("GET", "HEAD", "DELETE"):
                async with self._session.request(method, url, headers=headers) as resp:
                    body = await resp.read()
                    self.data_received.emit(body, url)
                    return True
            else:
                async with self._session.request(method, url, data=data, headers=headers) as resp:
                    body = await resp.read()
                    self.data_received.emit(body, url)
                    return True
        except Exception as e:
            self.error_occurred.emit(f"HTTP Client request failed: {e}")
            return False

    async def request(self, method: str, path: str, data: bytes = b"", headers: dict | None = None) -> bytes | None:
        if not self._session:
            self.error_occurred.emit("HTTP Client not started")
            return None
        try:
            url = f"http://{self.config.remote_host}:{self.config.remote_port}{path}"
            content_type = "application/json" if self.config.payload_type.value == "json" else "text/plain"
            if headers is None:
                headers = {}
            if "Content-Type" not in headers:
                headers["Content-Type"] = content_type
            headers.update(self._custom_headers)

            if method.upper() in ("GET", "HEAD", "DELETE"):
                async with self._session.request(method, url, headers=headers) as resp:
                    body = await resp.read()
                    self.data_received.emit(body, url)
                    return body
            else:
                async with self._session.request(method, url, data=data, headers=headers) as resp:
                    body = await resp.read()
                    self.data_received.emit(body, url)
                    return body
        except Exception as e:
            self.error_occurred.emit(f"HTTP Client request failed: {e}")
            return None
