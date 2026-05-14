from __future__ import annotations

import json
import re
from typing import Any

from protocol_workbench.core.models import MatchRule, MatchOperator


class ResponseMatcher:
    def match(self, data: Any, rules: list[MatchRule]) -> bool:
        if not rules:
            return True
        for rule in rules:
            if not self._match_single(data, rule):
                return False
        return True

    def _match_single(self, data: Any, rule: MatchRule) -> bool:
        value = self._resolve_path(data, rule.path)
        if rule.operator == MatchOperator.EXISTS:
            return value is not _MISSING

        if value is _MISSING:
            return False

        str_value = str(value)
        target = rule.value

        if rule.operator == MatchOperator.EQ:
            return str_value == target
        elif rule.operator == MatchOperator.NE:
            return str_value != target
        elif rule.operator == MatchOperator.CONTAINS:
            return target in str_value
        elif rule.operator == MatchOperator.REGEX:
            try:
                return bool(re.search(target, str_value))
            except re.error:
                return False
        return False

    def _resolve_path(self, data: Any, path: str) -> Any:
        if not path or not path.startswith("$"):
            return data.get(path) if isinstance(data, dict) else _MISSING

        parts = path.lstrip("$").lstrip(".").split(".")
        current = data
        for part in parts:
            if not part:
                continue
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return _MISSING
            elif isinstance(current, list):
                try:
                    idx = int(part.strip("[]"))
                    current = current[idx]
                except (ValueError, IndexError):
                    return _MISSING
            else:
                return _MISSING
        return current


_MISSING = object()
