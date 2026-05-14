from __future__ import annotations

import asyncio
from typing import Optional

try:
    import websockets
    from websockets.server import serve as ws_serve
    from websockets.exceptions import ConnectionClosed
except ImportError:
    websockets = None
    ConnectionClosed = None

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class WebSocketServerAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._server = None
        self._clients: dict[str, any] = {}

    async def start(self):
        if websockets is None:
            self.error_occurred.emit("websockets library not installed")
            self._set_state(self.STATE_ERROR)
            return
        try:
            ssl_context = None
            if self.config.path.startswith("wss://") or self.config.path.startswith("ssl"):
                import ssl
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.error_occurred.emit(
                    "WARNING: SSL enabled with verify_mode=CERT_NONE. "
                    "This is insecure and should only be used for testing. "
                    "Set ssl_certfile and ssl_keyfile for production use."
                )

            self._server = await ws_serve(
                self._handle_client,
                self.config.host,
                self.config.port,
                ssl=ssl_context,
            )
            self._set_state(self.STATE_LISTENING)
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"WebSocket Server start failed: {e}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._clients.clear()
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._clients:
            self.error_occurred.emit("WebSocket Server: no connected clients")
            return False
        try:
            if target and target in self._clients:
                await self._clients[target].send(data)
            else:
                for ws in list(self._clients.values()):
                    await ws.send(data)
            return True
        except Exception as e:
            self.error_occurred.emit(f"WebSocket Server send failed: {e}")
            return False

    async def _handle_client(self, websocket):
        addr = websocket.remote_address
        client_id = f"{addr[0]}:{addr[1]}" if addr else "unknown"
        self._clients[client_id] = websocket

        try:
            async for message in websocket:
                if isinstance(message, str):
                    data = message.encode("utf-8")
                else:
                    data = message
                self.data_received.emit(data, client_id)
        except Exception as e:
            if ConnectionClosed and isinstance(e, ConnectionClosed):
                pass
            else:
                self.error_occurred.emit(f"WebSocket Server client error: {e}")
        finally:
            if client_id in self._clients:
                del self._clients[client_id]

    def get_client_ids(self) -> list[str]:
        return list(self._clients.keys())
