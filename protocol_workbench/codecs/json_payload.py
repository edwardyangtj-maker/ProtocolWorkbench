from __future__ import annotations

import json
from typing import Any

from protocol_workbench.codecs.payload_base import PayloadCodec


class JsonPayloadCodec(PayloadCodec):
    def encode(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError:
                return data.encode("utf-8")
            return data.encode("utf-8")
        return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def decode(self, raw: bytes) -> Any:
        text = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def to_display(self, decoded: Any) -> str:
        if isinstance(decoded, (dict, list)):
            return json.dumps(decoded, ensure_ascii=False, indent=2)
        return str(decoded)
