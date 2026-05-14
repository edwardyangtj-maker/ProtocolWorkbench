from __future__ import annotations

from protocol_workbench.codecs.frame_base import FrameCodec
from protocol_workbench.core.models import FrameRule


class StartEndFrameCodec(FrameCodec):
    def __init__(self, rule: FrameRule):
        self.rule = rule
        self._buffer = bytearray()
        self._start_flag = (rule.start_flag or "").encode("utf-8")
        self._end_flag = (rule.end_flag or "").encode("utf-8")

    def encode(self, payload: bytes) -> bytes:
        result = bytearray()
        if self._start_flag:
            result.extend(self._start_flag)
        result.extend(payload)
        if self._end_flag:
            result.extend(self._end_flag)
        return bytes(result)

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames = []

        while True:
            if not self._start_flag and not self._end_flag:
                if self._buffer:
                    frames.append(bytes(self._buffer))
                    self._buffer.clear()
                break

            if self._start_flag:
                start_idx = self._buffer.find(self._start_flag)
                if start_idx == -1:
                    break
                self._buffer = self._buffer[start_idx + len(self._start_flag):]

            if self._end_flag:
                end_idx = self._buffer.find(self._end_flag)
                if end_idx == -1:
                    break
                frame = bytes(self._buffer[:end_idx])
                self._buffer = self._buffer[end_idx + len(self._end_flag):]
                if frame:
                    frames.append(frame)
            else:
                if self._buffer:
                    frames.append(bytes(self._buffer))
                    self._buffer.clear()
                break

        return frames

    def reset(self):
        self._buffer.clear()
