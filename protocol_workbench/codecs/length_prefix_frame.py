from __future__ import annotations

import struct
from protocol_workbench.codecs.frame_base import FrameCodec
from protocol_workbench.core.models import FrameRule


class LengthPrefixFrameCodec(FrameCodec):
    def __init__(self, rule: FrameRule):
        self.rule = rule
        self._buffer = bytearray()
        self._offset = rule.length_field_offset
        self._size = rule.length_field_size
        self._byte_order = rule.byte_order
        self._includes_header = rule.length_includes_header

        if self._size == 2:
            self._fmt_be = ">H"
            self._fmt_le = "<H"
        elif self._size == 4:
            self._fmt_be = ">I"
            self._fmt_le = "<I"
        elif self._size == 8:
            self._fmt_be = ">Q"
            self._fmt_le = "<Q"
        else:
            self._fmt_be = ">I"
            self._fmt_le = "<I"
            self._size = 4

    def encode(self, payload: bytes) -> bytes:
        header_size = self._offset + self._size
        length = len(payload)
        if self._includes_header:
            length += header_size

        header = bytearray(self._offset)
        fmt = self._fmt_be if self._byte_order == "big" else self._fmt_le
        header.extend(struct.pack(fmt, length))
        return bytes(header) + payload

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames = []

        while True:
            header_size = self._offset + self._size
            if len(self._buffer) < header_size:
                break

            length_bytes = self._buffer[self._offset:self._offset + self._size]
            fmt = self._fmt_be if self._byte_order == "big" else self._fmt_le
            body_length = struct.unpack(fmt, bytes(length_bytes))[0]

            if self._includes_header:
                total_length = body_length
            else:
                total_length = header_size + body_length

            if len(self._buffer) < total_length:
                break

            frame = bytes(self._buffer[header_size:total_length])
            self._buffer = self._buffer[total_length:]
            if frame:
                frames.append(frame)

        return frames

    def reset(self):
        self._buffer.clear()
