from __future__ import annotations

from protocol_workbench.codecs.frame_base import FrameCodec
from protocol_workbench.core.models import FrameRule


class DelimiterFrameCodec(FrameCodec):
    def __init__(self, rule: FrameRule):
        self.rule = rule
        self._buffer = bytearray()
        self._delimiter = self._unescape(rule.delimiter or "\n")

    @staticmethod
    def _unescape(s: str) -> bytes:
        return s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t").encode("utf-8")

    def encode(self, payload: bytes) -> bytes:
        return payload + self._delimiter

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames = []
        while True:
            idx = self._buffer.find(self._delimiter)
            if idx == -1:
                break
            frame = bytes(self._buffer[:idx])
            self._buffer = self._buffer[idx + len(self._delimiter):]
            if frame:
                frames.append(frame)
        return frames

    def reset(self):
        self._buffer.clear()
