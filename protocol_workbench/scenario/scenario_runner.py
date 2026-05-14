from __future__ import annotations

import asyncio
from typing import Optional

from PySide6.QtCore import QObject, Signal

from protocol_workbench.core.models import Scenario, ScenarioStep
from protocol_workbench.core.runtime_manager import RuntimeManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.scenario.step_executor import StepExecutor


class ScenarioRunner(QObject):
    scenario_started = Signal(str)
    scenario_step_started = Signal(str, int)
    scenario_step_completed = Signal(str, int, bool)
    scenario_completed = Signal(str, bool)

    def __init__(self, runtime: RuntimeManager, logger: LoggerService, parent=None):
        super().__init__(parent)
        self.runtime = runtime
        self.logger = logger
        self.executor = StepExecutor(runtime, logger)
        self._running_scenarios: dict[str, asyncio.Task] = {}

    def set_project(self, project):
        self.executor.set_project(project)

    async def run_scenario(self, scenario: Scenario):
        self.scenario_started.emit(scenario.id)
        self.logger.info(f"Scenario started: {scenario.name}")

        if scenario.parallel_policy == "parallel":
            all_success = await self._run_parallel(scenario)
        else:
            all_success = await self._run_sequential(scenario)

        self.scenario_completed.emit(scenario.id, all_success)
        self.logger.info(f"Scenario completed: {scenario.name} (success={all_success})")

    async def _run_sequential(self, scenario: Scenario) -> bool:
        sorted_steps = sorted(scenario.steps, key=lambda s: s.order)
        all_success = True
        for step in sorted_steps:
            self.scenario_step_started.emit(scenario.id, step.order)
            success = await self.executor.execute(step)
            self.scenario_step_completed.emit(scenario.id, step.order, success)
            if not success and scenario.stop_policy == "stop_on_error":
                all_success = False
                self.logger.warn(f"Scenario stopped on error at step {step.order}")
                break
            if not success:
                all_success = False
        return all_success

    async def _run_parallel(self, scenario: Scenario) -> bool:
        async def run_step(step):
            self.scenario_step_started.emit(scenario.id, step.order)
            success = await self.executor.execute(step)
            self.scenario_step_completed.emit(scenario.id, step.order, success)
            return success

        tasks = [run_step(step) for step in scenario.steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_success = True
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Step {scenario.steps[i].order} raised exception: {result}")
                all_success = False
            elif not result:
                all_success = False
        return all_success

    def start_scenario_async(self, scenario: Scenario):
        if scenario.id in self._running_scenarios:
            self.logger.warn(f"Scenario {scenario.name} already running")
            return

        task = asyncio.create_task(self.run_scenario(scenario))
        self._running_scenarios[scenario.id] = task

        def on_done(t):
            self._running_scenarios.pop(scenario.id, None)

        task.add_done_callback(on_done)

    async def stop_scenario(self, scenario_id: str):
        if scenario_id in self._running_scenarios:
            task = self._running_scenarios[scenario_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._running_scenarios.pop(scenario_id, None)

    def is_running(self, scenario_id: str) -> bool:
        return scenario_id in self._running_scenarios
