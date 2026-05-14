from __future__ import annotations

from typing import Any

from protocol_workbench.codecs.payload_base import PayloadCodec


class TextPayloadCodec(PayloadCodec):
    def encode(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        return str(data).encode("utf-8")

    def decode(self, raw: bytes) -> Any:
        return raw.decode("utf-8", errors="replace")

    def to_display(self, decoded: Any) -> str:
        return str(decoded)
