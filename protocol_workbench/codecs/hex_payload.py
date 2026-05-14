from __future__ import annotations

from typing import Any

from protocol_workbench.codecs.payload_base import PayloadCodec


class HexPayloadCodec(PayloadCodec):
    def encode(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        hex_str = str(data).replace(" ", "").replace("0x", "").replace(",", "")
        if len(hex_str) % 2 != 0:
            hex_str = "0" + hex_str
        return bytes.fromhex(hex_str)

    def decode(self, raw: bytes) -> Any:
        return raw.hex()

    def to_display(self, decoded: Any) -> str:
        hex_str = str(decoded)
        return " ".join(hex_str[i:i + 2] for i in range(0, len(hex_str), 2)).upper()
