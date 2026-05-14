from __future__ import annotations

import asyncio
from typing import Optional

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class TcpServerAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._server: asyncio.Server | None = None
        self._clients: dict[str, asyncio.StreamWriter] = {}
        self._accept_task: asyncio.Task | None = None

    async def start(self):
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                self.config.host,
                self.config.port,
            )
            self._set_state(self.STATE_LISTENING)
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"TCP Server start failed: {e}")

    async def stop(self):
        for client_id, writer in list(self._clients.items()):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        if self._server:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass
            self._server = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._clients:
            self.error_occurred.emit("TCP Server: no connected clients")
            return False
        try:
            if target and target in self._clients:
                writer = self._clients[target]
                writer.write(data)
                await writer.drain()
            else:
                for writer in list(self._clients.values()):
                    writer.write(data)
                    await writer.drain()
            return True
        except Exception as e:
            self.error_occurred.emit(f"TCP Server send failed: {e}")
            return False

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        client_id = f"{addr[0]}:{addr[1]}" if addr else "unknown"
        self._clients[client_id] = writer

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                self.data_received.emit(data, client_id)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            if client_id in self._clients:
                del self._clients[client_id]
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def get_client_ids(self) -> list[str]:
        return list(self._clients.keys())
