from __future__ import annotations

import asyncio
from typing import Optional

from protocol_workbench.transports.base import TransportAdapter
from protocol_workbench.core.models import EndpointConfig


class TcpClientAdapter(TransportAdapter):
    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(config, parent)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._read_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None

    async def start(self):
        self._set_state(self.STATE_CONNECTING)
        try:
            # 准备连接参数，仅当明确指定了本地端口(>0)时才绑定
            connect_kwargs = {}
            if self.config.host and self.config.port > 0:
                connect_kwargs["local_addr"] = (self.config.host, self.config.port)
            
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.remote_host,
                    self.config.remote_port,
                    **connect_kwargs,
                ),
                timeout=self.config.connect_timeout_ms / 1000.0,
            )
            self._set_state(self.STATE_CONNECTED)
            self._read_task = asyncio.create_task(self._read_loop())
        except Exception as e:
            self._set_state(self.STATE_ERROR)
            self.error_occurred.emit(f"TCP Client connect failed: {e}")
            if self.config.auto_reconnect:
                self._start_reconnect()

    async def stop(self):
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
        self._set_state(self.STATE_DISCONNECTED)

    async def send(self, data: bytes, target: str = "") -> bool:
        if not self._writer:
            self.error_occurred.emit("TCP Client not connected")
            return False
        try:
            self._writer.write(data)
            await self._writer.drain()
            return True
        except Exception as e:
            self.error_occurred.emit(f"TCP Client send failed: {e}")
            if self.config.auto_reconnect and self._state != self.STATE_DISCONNECTED:
                self._start_reconnect()
            return False

    async def _read_loop(self):
        try:
            while self._reader and not self._reader.at_eof():
                data = await self._reader.read(4096)
                if data:
                    self.data_received.emit(data, self.config.remote_host)
                else:
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.error_occurred.emit(f"TCP Client read error: {e}")
        finally:
            if self._state == self.STATE_CONNECTED:
                self._set_state(self.STATE_DISCONNECTED)
                if self.config.auto_reconnect:
                    self._start_reconnect()

    def _start_reconnect(self):
        if self._reconnect_task and not self._reconnect_task.done():
            return

        async def reconnect_loop():
            delay = 1
            max_delay = 30
            while self._state not in (self.STATE_DISCONNECTED, self.STATE_IDLE):
                if self._state == self.STATE_CONNECTED:
                    break
                await asyncio.sleep(delay)
                try:
                    self._set_state(self.STATE_CONNECTING)
                    # 准备连接参数，仅当明确指定了本地端口(>0)时才绑定
                    connect_kwargs = {}
                    if self.config.host and self.config.port > 0:
                        connect_kwargs["local_addr"] = (self.config.host, self.config.port)
                    
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            self.config.remote_host,
                            self.config.remote_port,
                            **connect_kwargs,
                        ),
                        timeout=self.config.connect_timeout_ms / 1000.0,
                    )
                    self._set_state(self.STATE_CONNECTED)
                    self._read_task = asyncio.create_task(self._read_loop())
                    self.error_occurred.emit(f"TCP Client reconnected to {self.config.remote_host}:{self.config.remote_port}")
                    break
                except Exception as e:
                    self._set_state(self.STATE_ERROR)
                    self.error_occurred.emit(f"TCP Client reconnect failed: {e}, retry in {delay}s")
                    delay = min(delay * 2, max_delay)

        self._reconnect_task = asyncio.create_task(reconnect_loop())
