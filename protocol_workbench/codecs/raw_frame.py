from __future__ import annotations

from protocol_workbench.codecs.frame_base import FrameCodec
from protocol_workbench.core.models import FrameRule


class RawFrameCodec(FrameCodec):
    def __init__(self, rule: FrameRule):
        self.rule = rule

    def encode(self, payload: bytes) -> bytes:
        return payload

    def feed(self, data: bytes) -> list[bytes]:
        if data:
            return [data]
        return []

    def reset(self):
        pass
