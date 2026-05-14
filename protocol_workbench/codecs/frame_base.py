from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from protocol_workbench.core.models import FrameRule


class FrameCodec(ABC):
    @abstractmethod
    def encode(self, payload: bytes) -> bytes:
        pass

    @abstractmethod
    def feed(self, data: bytes) -> list[bytes]:
        pass

    @abstractmethod
    def reset(self):
        pass

    @staticmethod
    def create(rule: FrameRule) -> FrameCodec:
        from protocol_workbench.codecs.raw_frame import RawFrameCodec
        from protocol_workbench.codecs.delimiter_frame import DelimiterFrameCodec
        from protocol_workbench.codecs.start_end_frame import StartEndFrameCodec
        from protocol_workbench.codecs.length_prefix_frame import LengthPrefixFrameCodec

        from protocol_workbench.core.models import FrameMode

        if rule.mode == FrameMode.RAW:
            return RawFrameCodec(rule)
        elif rule.mode == FrameMode.DELIMITER:
            return DelimiterFrameCodec(rule)
        elif rule.mode == FrameMode.START_END:
            return StartEndFrameCodec(rule)
        elif rule.mode == FrameMode.LENGTH_PREFIX:
            return LengthPrefixFrameCodec(rule)
        else:
            return RawFrameCodec(rule)
