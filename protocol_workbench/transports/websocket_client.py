from __future__ import annotations

import asyncio
from typing import Optional

try:
    import websockets
    from websockets.client import connect as ws_connect
except ImportError:
    websockets = None

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class WebSocketClientAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._ws = None
        self._read_task: asyncio.Task | None = None

    async def start(self):
        if websockets is None:
            self.error_occurred.emit("websockets library not installed")
            self._set_state(self.STATE_ERROR)
            return
        self._set_state(self.STATE_CONNECTING)
        try:
            scheme = "wss" if self.config.path.startswith("wss://") else "ws"
            if self.config.path.startswith("wss://") or self.config.path.startswith("ws://"):
                url = self.config.path
            else:
                host = self.config.remote_host
                port = self.config.remote_port
                path = self.config.path
                url = f"{scheme}://{host}:{port}{path}"
            ssl_context = None
            if scheme == "wss":
                import ssl
                ssl_context = ssl.create_default_context()
            
            # 准备连接参数，绑定本地IP和端口（如果配置了）
            connect_kwargs = {}
            if self.config.host and self.config.port:
                connect_kwargs["local_addr"] = (self.config.host, self.config.port)
            
            self._ws = await asyncio.wait_for(
                ws_connect(url, ssl=ssl_context, **connect_kwargs),
                timeout=self.config.connect_timeout_ms / 1000.0,
            )
            self._set_state(self.STATE_CONNECTED)
            self._read_task = asyncio.create_task(self._read_loop())
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"WebSocket Client connect failed: {e}")

    async def stop(self):
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._ws:
            self.error_occurred.emit("WebSocket Client not connected")
            return False
        try:
            await self._ws.send(data)
            return True
        except Exception as e:
            self.error_occurred.emit(f"WebSocket Client send failed: {e}")
            return False

    async def _read_loop(self):
        try:
            async for message in self._ws:
                if isinstance(message, str):
                    data = message.encode("utf-8")
                else:
                    data = message
                self.data_received.emit(data, self.config.remote_host)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._state == self.STATE_CONNECTED:
                self.error_occurred.emit(f"WebSocket Client read error: {e}")
        finally:
            if self._state == self.STATE_CONNECTED:
                self._set_state(self.STATE_DISCONNECTED)
