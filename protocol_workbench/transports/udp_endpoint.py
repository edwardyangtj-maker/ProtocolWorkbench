from __future__ import annotations

import asyncio
from typing import Optional

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class UdpEndpointAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._transport: asyncio.DatagramTransport | None = None
        self._read_task: asyncio.Task | None = None

    async def start(self):
        try:
            loop = asyncio.get_running_loop()
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: UdpProtocol(self),
                local_addr=(self.config.host, self.config.port),
            )
            self._set_state(self.STATE_LISTENING)
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"UDP Endpoint start failed: {e}")

    async def stop(self):
        if self._transport:
            self._transport.close()
            self._transport = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._transport:
            self.error_occurred.emit("UDP Endpoint not started")
            return False
        try:
            if target:
                parts = target.split(":")
                host = parts[0] if parts else self.config.remote_host
                port = int(parts[1]) if len(parts) > 1 else self.config.remote_port
            else:
                host = self.config.remote_host
                port = self.config.remote_port
            self._transport.sendto(data, (host, port))
            return True
        except Exception as e:
            self.error_occurred.emit(f"UDP send failed: {e}")
            return False

    def _on_datagram_received(self, data: bytes, addr: tuple):
        client_id = f"{addr[0]}:{addr[1]}"
        self.data_received.emit(data, client_id)


class UdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, adapter: UdpEndpointAdapter):
        self.adapter = adapter

    def datagram_received(self, data: bytes, addr: tuple):
        self.adapter._on_datagram_received(data, addr)

    def error_received(self, exc: Exception):
        self.adapter.error_occurred.emit(f"UDP error: {exc}")

    def connection_made(self, transport):
        pass

    def connection_lost(self, exc):
        pass
