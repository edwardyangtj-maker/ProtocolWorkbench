from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QInputDialog, QMessageBox,
)

from protocol_workbench.core.models import (
    Scenario, ScenarioStep, StepType, MatchRule, MatchOperator,
)
from protocol_workbench.core.project_manager import ProjectManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.scenario.scenario_runner import ScenarioRunner


class ScenarioPanel(QWidget):
    def __init__(self, scenario_runner: ScenarioRunner, project_manager: ProjectManager,
                 logger: LoggerService, parent=None):
        super().__init__(parent)
        self.scenario_runner = scenario_runner
        self.project_manager = project_manager
        self.logger = logger
        self.current_scenario: Scenario | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()
        self.scenario_combo = QComboBox()
        self.scenario_combo.setMinimumWidth(200)
        top_layout.addWidget(QLabel("场景:"), 0)
        top_layout.addWidget(self.scenario_combo, 1)

        self.new_btn = QPushButton("+ 新建场景")
        self.new_btn.clicked.connect(self._new_scenario)
        top_layout.addWidget(self.new_btn)

        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.setProperty("class", "success")
        self.run_btn.clicked.connect(self._run_scenario)
        top_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_scenario)
        top_layout.addWidget(self.stop_btn)

        layout.addLayout(top_layout)

        info_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("场景名称")
        info_layout.addWidget(QLabel("名称:"), 0)
        info_layout.addWidget(self.name_edit, 2)

        self.stop_policy_combo = QComboBox()
        self.stop_policy_combo.addItem("出错停止", "stop_on_error")
        self.stop_policy_combo.addItem("继续执行", "continue_on_error")
        info_layout.addWidget(QLabel("停止策略:"), 0)
        info_layout.addWidget(self.stop_policy_combo, 1)

        self.parallel_policy_combo = QComboBox()
        self.parallel_policy_combo.addItem("串行执行", "sequential")
        self.parallel_policy_combo.addItem("并行执行", "parallel")
        info_layout.addWidget(QLabel("执行策略:"), 0)
        info_layout.addWidget(self.parallel_policy_combo, 1)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.clicked.connect(self._save_scenario)
        info_layout.addWidget(self.save_btn)

        layout.addLayout(info_layout)

        steps_group = QGroupBox("场景步骤")
        steps_layout = QVBoxLayout(steps_group)

        steps_toolbar = QHBoxLayout()
        self.add_step_btn = QPushButton("+ 添加步骤")
        self.add_step_btn.clicked.connect(self._add_step)
        steps_toolbar.addWidget(self.add_step_btn)

        self.del_step_btn = QPushButton("🗑 删除步骤")
        self.del_step_btn.clicked.connect(self._delete_step)
        steps_toolbar.addWidget(self.del_step_btn)

        self.move_up_btn = QPushButton("⬆ 上移")
        self.move_up_btn.clicked.connect(self._move_step_up)
        steps_toolbar.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("⬇ 下移")
        self.move_down_btn.clicked.connect(self._move_step_down)
        steps_toolbar.addWidget(self.move_down_btn)

        steps_toolbar.addStretch()
        steps_layout.addLayout(steps_toolbar)

        self.step_table = QTableWidget()
        self.step_table.setColumnCount(8)
        self.step_table.setHorizontalHeaderLabels(["序号", "类型", "端点", "模板", "超时(ms)", "延时(ms)", "数据源", "数据格式"])
        header = self.step_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 50)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 80)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.resizeSection(7, 80)
        self.step_table.setAlternatingRowColors(True)
        self.step_table.setSelectionBehavior(QTableWidget.SelectRows)
        steps_layout.addWidget(self.step_table)

        layout.addWidget(steps_group)

        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_selected)

    def refresh(self):
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        project = self.project_manager.current_project
        if project:
            for sc in project.scenarios:
                self.scenario_combo.addItem(sc.name, sc.id)
        self.scenario_combo.blockSignals(False)

        if self.scenario_combo.count() > 0:
            self._on_scenario_selected(0)

    def select_scenario(self, scenario_id: str):
        for i in range(self.scenario_combo.count()):
            if self.scenario_combo.itemData(i) == scenario_id:
                self.scenario_combo.setCurrentIndex(i)
                break

    def _on_scenario_selected(self, index: int):
        if index < 0:
            return
        sc_id = self.scenario_combo.itemData(index)
        project = self.project_manager.current_project
        if project:
            for sc in project.scenarios:
                if sc.id == sc_id:
                    self.current_scenario = sc
                    self._load_scenario(sc)
                    break

    def _load_scenario(self, sc: Scenario):
        self.name_edit.setText(sc.name)
        idx = self.stop_policy_combo.findData(sc.stop_policy)
        if idx >= 0:
            self.stop_policy_combo.setCurrentIndex(idx)
        idx = self.parallel_policy_combo.findData(sc.parallel_policy)
        if idx >= 0:
            self.parallel_policy_combo.setCurrentIndex(idx)

        self.step_table.setRowCount(0)
        project = self.project_manager.current_project
        for row, step in enumerate(sorted(sc.steps, key=lambda s: s.order)):
            self.step_table.insertRow(row)
            self.step_table.setItem(row, 0, QTableWidgetItem(str(step.order)))

            type_combo = QComboBox()
            for st in StepType:
                type_combo.addItem(st.value, st.value)
            idx = type_combo.findData(step.type.value)
            if idx >= 0:
                type_combo.setCurrentIndex(idx)
            self.step_table.setCellWidget(row, 1, type_combo)

            ep_combo = QComboBox()
            if project:
                for ep in project.endpoints:
                    ep_combo.addItem(ep.name, ep.id)
            idx = ep_combo.findData(step.endpoint_id)
            if idx >= 0:
                ep_combo.setCurrentIndex(idx)
            self.step_table.setCellWidget(row, 2, ep_combo)

            tpl_combo = QComboBox()
            if project:
                for tpl in project.message_templates:
                    tpl_combo.addItem(tpl.name, tpl.id)
            idx = tpl_combo.findData(step.template_id)
            if idx >= 0:
                tpl_combo.setCurrentIndex(idx)
            self.step_table.setCellWidget(row, 3, tpl_combo)

            self.step_table.setItem(row, 4, QTableWidgetItem(str(step.timeout_ms)))
            self.step_table.setItem(row, 5, QTableWidgetItem(str(step.delay_ms)))
            self.step_table.setItem(row, 6, QTableWidgetItem(step.data_source_path))

            fmt_combo = QComboBox()
            fmt_combo.addItem("JSON", "json")
            fmt_combo.addItem("CSV", "csv")
            idx = fmt_combo.findData(step.data_source_format)
            if idx >= 0:
                fmt_combo.setCurrentIndex(idx)
            self.step_table.setCellWidget(row, 7, fmt_combo)

    def _new_scenario(self):
        from protocol_workbench.core.models import new_id
        project = self.project_manager.current_project
        if not project:
            return
        name, ok = QInputDialog.getText(self, "新建场景", "场景名称:", text="新场景")
        if ok and name:
            sc = Scenario(id=new_id(), name=name)
            project.scenarios.append(sc)
            self.refresh()
            self.logger.info(f"新建场景: {name}")

    def _save_scenario(self):
        if not self.current_scenario:
            return
        sc = self.current_scenario
        sc.name = self.name_edit.text()
        sc.stop_policy = self.stop_policy_combo.currentData()
        sc.parallel_policy = self.parallel_policy_combo.currentData()

        steps = []
        for row in range(self.step_table.rowCount()):
            step = ScenarioStep(order=row)
            type_widget = self.step_table.cellWidget(row, 1)
            if type_widget:
                step.type = StepType(type_widget.currentData())
            ep_widget = self.step_table.cellWidget(row, 2)
            if ep_widget:
                step.endpoint_id = ep_widget.currentData() or ""
            tpl_widget = self.step_table.cellWidget(row, 3)
            if tpl_widget:
                step.template_id = tpl_widget.currentData() or ""
            timeout_item = self.step_table.item(row, 4)
            if timeout_item:
                try:
                    step.timeout_ms = int(timeout_item.text())
                except ValueError:
                    pass
            delay_item = self.step_table.item(row, 5)
            if delay_item:
                try:
                    step.delay_ms = int(delay_item.text())
                except ValueError:
                    pass
            ds_item = self.step_table.item(row, 6)
            if ds_item:
                step.data_source_path = ds_item.text()
            fmt_widget = self.step_table.cellWidget(row, 7)
            if fmt_widget:
                step.data_source_format = fmt_widget.currentData() or "json"
            steps.append(step)

        sc.steps = steps
        self.refresh()
        self.logger.info(f"场景已保存: {sc.name}")

    def _run_scenario(self):
        if self.current_scenario:
            self._save_scenario()
            self.scenario_runner.start_scenario_async(self.current_scenario)
            self.logger.info(f"场景开始运行: {self.current_scenario.name}")

    def _stop_scenario(self):
        if self.current_scenario:
            asyncio.create_task(self.scenario_runner.stop_scenario(self.current_scenario.id))

    def _add_step(self):
        row = self.step_table.rowCount()
        self.step_table.insertRow(row)
        self.step_table.setItem(row, 0, QTableWidgetItem(str(row)))

        type_combo = QComboBox()
        for st in StepType:
            type_combo.addItem(st.value, st.value)
        self.step_table.setCellWidget(row, 1, type_combo)

        ep_combo = QComboBox()
        project = self.project_manager.current_project
        if project:
            for ep in project.endpoints:
                ep_combo.addItem(ep.name, ep.id)
        self.step_table.setCellWidget(row, 2, ep_combo)

        tpl_combo = QComboBox()
        if project:
            for tpl in project.message_templates:
                tpl_combo.addItem(tpl.name, tpl.id)
        self.step_table.setCellWidget(row, 3, tpl_combo)

        self.step_table.setItem(row, 4, QTableWidgetItem("10000"))
        self.step_table.setItem(row, 5, QTableWidgetItem("0"))
        self.step_table.setItem(row, 6, QTableWidgetItem(""))

        fmt_combo = QComboBox()
        fmt_combo.addItem("JSON", "json")
        fmt_combo.addItem("CSV", "csv")
        self.step_table.setCellWidget(row, 7, fmt_combo)

    def _delete_step(self):
        row = self.step_table.currentRow()
        if row >= 0:
            self.step_table.removeRow(row)

    def _move_step_up(self):
        row = self.step_table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.step_table.selectRow(row - 1)

    def _move_step_down(self):
        row = self.step_table.currentRow()
        if row < self.step_table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.step_table.selectRow(row + 1)

    def _swap_rows(self, row1: int, row2: int):
        for col in range(self.step_table.columnCount()):
            widget1 = self.step_table.cellWidget(row1, col)
            widget2 = self.step_table.cellWidget(row2, col)

            if widget1 or widget2:
                if widget1:
                    self.step_table.removeCellWidget(row1, col)
                if widget2:
                    self.step_table.removeCellWidget(row2, col)
                if widget1:
                    self.step_table.setCellWidget(row2, col, widget1)
                if widget2:
                    self.step_table.setCellWidget(row1, col, widget2)
            else:
                item1 = self.step_table.takeItem(row1, col)
                item2 = self.step_table.takeItem(row2, col)
                if item1:
                    self.step_table.setItem(row2, col, item1)
                if item2:
                    self.step_table.setItem(row1, col, item2)
