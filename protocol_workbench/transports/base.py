from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from protocol_workbench.core.models import EndpointConfig, LogRecord


class TransportAdapter(QObject):
    data_received = Signal(bytes, str)
    state_changed = Signal(str, str)
    error_occurred = Signal(str)

    STATE_IDLE = "idle"
    STATE_CONNECTING = "connecting"
    STATE_CONNECTED = "connected"
    STATE_LISTENING = "listening"
    STATE_DISCONNECTED = "disconnected"
    STATE_ERROR = "error"

    def __init__(self, config: EndpointConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._state = self.STATE_IDLE

    @property
    def state(self) -> str:
        return self._state

    def _set_state(self, state: str):
        self._state = state
        self.state_changed.emit(self.config.id, state)

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def send(self, data: bytes, target: str = "") -> bool:
        pass

    def is_running(self) -> bool:
        return self._state in (self.STATE_CONNECTED, self.STATE_LISTENING)
