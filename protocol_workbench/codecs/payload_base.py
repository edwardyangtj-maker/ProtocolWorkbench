from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from protocol_workbench.core.models import PayloadType


class PayloadCodec(ABC):
    @abstractmethod
    def encode(self, data: Any) -> bytes:
        pass

    @abstractmethod
    def decode(self, raw: bytes) -> Any:
        pass

    @abstractmethod
    def to_display(self, decoded: Any) -> str:
        pass

    @staticmethod
    def create(payload_type: PayloadType) -> PayloadCodec:
        from protocol_workbench.codecs.json_payload import JsonPayloadCodec
        from protocol_workbench.codecs.text_payload import TextPayloadCodec
        from protocol_workbench.codecs.hex_payload import HexPayloadCodec

        if payload_type == PayloadType.JSON:
            return JsonPayloadCodec()
        elif payload_type == PayloadType.TEXT:
            return TextPayloadCodec()
        elif payload_type == PayloadType.HEX:
            return HexPayloadCodec()
        else:
            return TextPayloadCodec()
