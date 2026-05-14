from __future__ import annotations

import re
import uuid
import random
import time
from datetime import datetime
from typing import Any


class VariableEngine:
    BUILTIN_VARIABLES = {
        "uuid": lambda: uuid.uuid4().hex,
        "uuid_short": lambda: uuid.uuid4().hex[:8],
        "now_ms": lambda: str(int(time.time() * 1000)),
        "timestamp": lambda: str(int(time.time())),
        "random_int": lambda: str(random.randint(0, 999999)),
        "random_int_100": lambda: str(random.randint(0, 100)),
        "date": lambda: datetime.now().strftime("%Y-%m-%d"),
        "time": lambda: datetime.now().strftime("%H:%M:%S"),
        "datetime": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "datetime_ms": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
    }

    VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self):
        self._env_variables: dict[str, str] = {}
        self._project_variables: dict[str, str] = {}
        self._runtime_variables: dict[str, str] = {}

    def set_env_variables(self, variables: dict[str, str]):
        self._env_variables = dict(variables)

    def set_project_variables(self, variables: dict[str, str]):
        self._project_variables = dict(variables)

    def set_runtime_variable(self, key: str, value: str):
        self._runtime_variables[key] = value

    def set_runtime_variables(self, variables: dict[str, str]):
        self._runtime_variables.update(variables)

    def clear_runtime_variables(self):
        self._runtime_variables.clear()

    def get_variable(self, name: str) -> str | None:
        if name in self._runtime_variables:
            return self._runtime_variables[name]
        if name in self._env_variables:
            return self._env_variables[name]
        if name in self._project_variables:
            return self._project_variables[name]
        if name in self.BUILTIN_VARIABLES:
            return self.BUILTIN_VARIABLES[name]()
        return None

    def resolve(self, text: str) -> str:
        if not text or "${" not in text:
            return text

        def replacer(match):
            var_name = match.group(1)
            value = self.get_variable(var_name)
            if value is not None:
                return value
            return match.group(0)

        return self.VAR_PATTERN.sub(replacer, text)

    def extract_variable_names(self, text: str) -> list[str]:
        return list(set(self.VAR_PATTERN.findall(text)))

    def get_all_variables(self) -> dict[str, str]:
        result = {}
        result.update(self._project_variables)
        result.update(self._env_variables)
        result.update(self._runtime_variables)
        return result
