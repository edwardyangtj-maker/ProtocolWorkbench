from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from protocol_workbench.core.models import ScenarioStep, Scenario, MatchRule
from protocol_workbench.core.runtime_manager import RuntimeManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.core.response_matcher import ResponseMatcher


class StepExecutor:
    def __init__(self, runtime: RuntimeManager, logger: LoggerService):
        self.runtime = runtime
        self.logger = logger
        self.matcher = ResponseMatcher()
        self._project = None
        self._last_received_data: dict[str, Any] = {}
        self.runtime.data_received.connect(self._on_data_received)

    def set_project(self, project):
        self._project = project

    async def execute(self, step: ScenarioStep) -> bool:
        self.logger.info(f"Executing step: {step.type.value} (order: {step.order})")
        try:
            if step.type.value == "start_endpoint":
                return await self._start_endpoint(step)
            elif step.type.value == "stop_endpoint":
                return await self._stop_endpoint(step)
            elif step.type.value == "send_message":
                return await self._send_message(step)
            elif step.type.value == "wait_message":
                return await self._wait_message(step)
            elif step.type.value == "auto_reply":
                return await self._auto_reply(step)
            elif step.type.value == "delay":
                return await self._delay(step)
            elif step.type.value == "assert_json":
                return await self._assert_json(step)
            elif step.type.value == "loop":
                return await self._loop(step)
            else:
                self.logger.warn(f"Unknown step type: {step.type}")
                return False
        except Exception as e:
            self.logger.error(f"Step execution failed: {e}")
            return False

    async def _start_endpoint(self, step: ScenarioStep) -> bool:
        if not self._project:
            return False
        endpoint = self._find_endpoint(step.endpoint_id)
        if endpoint:
            await self.runtime.start_endpoint(endpoint)
            return True
        return False

    async def _stop_endpoint(self, step: ScenarioStep) -> bool:
        await self.runtime.stop_endpoint(step.endpoint_id)
        return True

    async def _send_message(self, step: ScenarioStep) -> bool:
        template = self._find_template(step.template_id)
        if not template:
            return False

        if step.data_source_path:
            data_rows = self._load_data_source(step.data_source_path, step.data_source_format)
            if not data_rows:
                self.logger.error(f"Data source empty or not found: {step.data_source_path}")
                return False
            all_success = True
            for row_data in data_rows:
                for key, value in row_data.items():
                    self.runtime.variable_engine.set_runtime_variable(key, str(value))
                success = await self.runtime.send_message(step.endpoint_id, template)
                if not success:
                    all_success = False
                if step.delay_ms > 0:
                    await asyncio.sleep(step.delay_ms / 1000.0)
            return all_success

        return await self.runtime.send_message(step.endpoint_id, template)

    def _load_data_source(self, path: str, fmt: str) -> list[dict]:
        import csv
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            self.logger.error(f"Data source file not found: {path}")
            return []
        try:
            if fmt == "csv":
                with open(p, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            else:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return [data]
                    return []
        except Exception as e:
            self.logger.error(f"Failed to load data source: {e}")
            return []

    async def _wait_message(self, step: ScenarioStep) -> bool:
        future = self.runtime.create_wait_future(step.endpoint_id, step.matcher)
        if future is None:
            self.logger.warn(f"Endpoint {step.endpoint_id} not running, fallback to sleep")
            await asyncio.sleep(step.timeout_ms / 1000.0)
            return bool(self._last_received_data.get(step.endpoint_id))

        try:
            await asyncio.wait_for(future, timeout=step.timeout_ms / 1000.0)
            self.logger.info(f"Message received on endpoint {step.endpoint_id}")
            return True
        except asyncio.TimeoutError:
            self.logger.warn(f"Wait message timeout on endpoint {step.endpoint_id}")
            return False

    async def _auto_reply(self, step: ScenarioStep) -> bool:
        template = self._find_template(step.template_id)
        if template:
            self.runtime.add_auto_reply(step.endpoint_id, step.matcher, template)
            return True
        return False

    async def _delay(self, step: ScenarioStep) -> bool:
        await asyncio.sleep(step.delay_ms / 1000.0)
        return True

    async def _assert_json(self, step: ScenarioStep) -> bool:
        if not step.assert_rules:
            self.logger.warn("Assert step has no rules, passing by default")
            return True

        import json as _json
        last_data = self._last_received_data.get(step.endpoint_id)
        if last_data is None:
            self.logger.error(f"Assert failed: no received data for endpoint {step.endpoint_id}")
            return False

        data_dict = None
        if isinstance(last_data, dict):
            data_dict = last_data
        elif isinstance(last_data, str):
            try:
                data_dict = _json.loads(last_data)
            except _json.JSONDecodeError:
                self.logger.error("Assert failed: received data is not valid JSON")
                return False

        if data_dict is None:
            self.logger.error("Assert failed: cannot parse received data")
            return False

        result = self.matcher.match(data_dict, step.assert_rules)
        if result:
            self.logger.info(f"Assert passed: {len(step.assert_rules)} rule(s)")
        else:
            self.logger.warn(f"Assert failed: {len(step.assert_rules)} rule(s)")
        return result

    async def _loop(self, step: ScenarioStep) -> bool:
        count = max(1, step.loop_count)
        all_success = True
        for i in range(count):
            self.logger.info(f"Loop iteration {i + 1}/{count}")
            inner_type = step.type
            if inner_type == StepType.LOOP:
                self.logger.warn("Nested loop not supported, treating as delay")
                await asyncio.sleep(step.delay_ms / 1000.0 if step.delay_ms > 0 else 0.1)
                continue

            inner_step = ScenarioStep(
                order=step.order,
                type=inner_type if inner_type != StepType.LOOP else StepType.DELAY,
                endpoint_id=step.endpoint_id,
                template_id=step.template_id,
                timeout_ms=step.timeout_ms,
                delay_ms=step.delay_ms,
                matcher=step.matcher,
                assert_rules=step.assert_rules,
            )
            success = await self.execute(inner_step)
            if not success:
                all_success = False
            if i < count - 1 and step.delay_ms > 0:
                await asyncio.sleep(step.delay_ms / 1000.0)
        return all_success

    def _find_endpoint(self, endpoint_id: str):
        if not self._project:
            return None
        for ep in self._project.endpoints:
            if ep.id == endpoint_id:
                return ep
        return None

    def _find_template(self, template_id: str):
        if not self._project:
            return None
        for t in self._project.message_templates:
            if t.id == template_id:
                return t
        return None

    def _on_data_received(self, endpoint_id: str, data: bytes, remote_addr: str):
        try:
            text = data.decode("utf-8", errors="replace")
            parsed = json.loads(text)
            self._last_received_data[endpoint_id] = parsed
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._last_received_data[endpoint_id] = data
