from __future__ import annotations

import json
import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSplitter, QInputDialog, QMessageBox,
    QTextEdit, QTabWidget, QCheckBox, QSpinBox,
)

from protocol_workbench.core.models import (
    MessageTemplate, TemplateCategory, PayloadType,
    MatchRule, MatchOperator, AckConfig, ResponseConfig,
    HeartbeatConfig, HeartbeatMode, FailAction, SendMode,
    FrameRule, FrameMode, JsonNode, JsonNodeType,
)
from protocol_workbench.core.project_manager import ProjectManager
from protocol_workbench.core.template_engine import TemplateEngine
from protocol_workbench.core.logger_service import LoggerService

CATEGORY_LABEL_MAP = {
    "cmd_laser": "命令-激光器",
    "cmd_camera": "命令-相机",
    "cmd_range": "命令-测距",
    "cmd_turntable": "命令-转台",
    "cmd_power": "命令-上下电",
    "cmd_connect": "命令-连接",
    "param_scan_config": "参数-扫描配置",
    "param_monitor_point": "参数-测距点",
    "param_range_param": "参数-测距参数",
    "param_imaging_param": "参数-成像参数",
    "param_camera_param": "参数-相机参数",
    "param_fan_param": "参数-风扇参数",
    "query_component": "查询-组件状态",
    "query_range_config": "查询-测距配置",
    "query_camera_calib": "查询-相机标定",
    "report_device_status": "上报-设备状态",
    "report_alarm": "上报-告警",
    "report_img": "上报-成像",
    "report_high_range": "上报-高精度",
    "report_range_result": "上报-测距结果",
    "report_task": "上报-任务",
    "response": "响应",
    "ack": "ACK",
    "heartbeat": "心跳",
    "message": "通用消息",
    "http_request": "HTTP请求",
    "tcp_message": "TCP消息",
    "ws_message": "WebSocket",
    "udp_message": "UDP消息",
}


class TemplatePanel(QWidget):
    edit_template_requested = Signal(str)

    def __init__(self, project_manager: ProjectManager, template_engine: TemplateEngine,
                 logger: LoggerService, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.template_engine = template_engine
        self.logger = logger
        self._filtered_endpoint_ids: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("🔍 全部模板", "all")
        self.filter_combo.insertSeparator(999)
        self.filter_combo.addItem("── 命令帧 ────────────", "__sep_cmd__")
        self.filter_combo.addItem("  激光器控制", "cmd_laser")
        self.filter_combo.addItem("  相机控制", "cmd_camera")
        self.filter_combo.addItem("  测距/高精度测距", "cmd_range")
        self.filter_combo.addItem("  转台控制", "cmd_turntable")
        self.filter_combo.addItem("  上下电", "cmd_power")
        self.filter_combo.addItem("  组件连接", "cmd_connect")
        self.filter_combo.addItem("── 参数帧 ────────────", "__sep_param__")
        self.filter_combo.addItem("  扫描配置", "param_scan_config")
        self.filter_combo.addItem("  测距点配置", "param_monitor_point")
        self.filter_combo.addItem("  测距参数", "param_range_param")
        self.filter_combo.addItem("  成像参数", "param_imaging_param")
        self.filter_combo.addItem("  相机/标定参数", "param_camera_param")
        self.filter_combo.addItem("  风扇参数", "param_fan_param")
        self.filter_combo.addItem("── 查询帧 ────────────", "__sep_query__")
        self.filter_combo.addItem("  组件状态查询", "query_component")
        self.filter_combo.addItem("  测距配置查询", "query_range_config")
        self.filter_combo.addItem("  相机标定点查询", "query_camera_calib")
        self.filter_combo.addItem("── 上报帧 ────────────", "__sep_report__")
        self.filter_combo.addItem("  设备状态上报", "report_device_status")
        self.filter_combo.addItem("  告警上报", "report_alarm")
        self.filter_combo.addItem("  成像上报", "report_img")
        self.filter_combo.addItem("  高精度测距上报", "report_high_range")
        self.filter_combo.addItem("  测距结果上报", "report_range_result")
        self.filter_combo.addItem("  任务上报", "report_task")
        self.filter_combo.addItem("── 响应/ACK ──────────", "__sep_resp__")
        self.filter_combo.addItem("  响应帧", "response")
        self.filter_combo.addItem("  ACK", "ack")
        self.filter_combo.addItem("  心跳", "heartbeat")
        self.filter_combo.addItem("── 通用 ──────────────", "__sep_general__")
        self.filter_combo.addItem("  通用消息", "message")
        self.filter_combo.addItem("  HTTP请求", "http_request")
        self.filter_combo.addItem("  TCP消息", "tcp_message")

        top_layout.addWidget(QLabel("筛选:"), 0)
        top_layout.addWidget(self.filter_combo, 1)

        self.new_btn = QPushButton("+ 新建模板")
        self.new_btn.setProperty("class", "primary")
        self.new_btn.clicked.connect(self._new_template)
        top_layout.addWidget(self.new_btn)

        self.filter_combo.currentIndexChanged.connect(self._filter_templates)

        layout.addLayout(top_layout)

        self.env_mode_label = QLabel("")
        layout.addWidget(self.env_mode_label)

        self.template_table = QTableWidget()
        self.template_table.setColumnCount(5)
        self.template_table.setHorizontalHeaderLabels(["名称", "分类", "Payload", "发送模式", "操作"])
        header = self.template_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 100)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 80)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 340)
        self.template_table.setAlternatingRowColors(True)
        self.template_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.template_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.template_table.verticalHeader().setDefaultSectionSize(42)

        layout.addWidget(self.template_table)

        detail_group = QGroupBox("模板详情")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_tabs = QTabWidget()

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        self.detail_content = QTextEdit()
        self.detail_content.setReadOnly(True)
        self.detail_content.setMaximumHeight(200)
        content_layout.addWidget(self.detail_content)
        self.detail_tabs.addTab(content_widget, "内容")

        match_widget = QWidget()
        match_layout = QVBoxLayout(match_widget)
        self.match_table = QTableWidget()
        self.match_table.setColumnCount(3)
        self.match_table.setHorizontalHeaderLabels(["Path", "操作符", "值"])
        self.match_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.match_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.match_table.horizontalHeader().resizeSection(1, 100)
        self.match_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        match_layout.addWidget(self.match_table)
        self.detail_tabs.addTab(match_widget, "匹配规则")

        ack_widget = QWidget()
        ack_layout = QFormLayout(ack_widget)
        self.ack_enabled_label = QLabel()
        ack_layout.addRow("启用ACK:", self.ack_enabled_label)
        self.ack_timeout_label = QLabel()
        ack_layout.addRow("ACK超时:", self.ack_timeout_label)
        self.ack_auto_label = QLabel()
        ack_layout.addRow("自动回复:", self.ack_auto_label)
        self.detail_tabs.addTab(ack_widget, "ACK配置")

        response_widget = QWidget()
        response_layout = QFormLayout(response_widget)
        self.resp_enabled_label = QLabel()
        response_layout.addRow("启用Response:", self.resp_enabled_label)
        self.resp_timeout_label = QLabel()
        response_layout.addRow("Response超时:", self.resp_timeout_label)
        self.detail_tabs.addTab(response_widget, "Response配置")

        heartbeat_widget = QWidget()
        heartbeat_layout = QFormLayout(heartbeat_widget)
        self.hb_enabled_label = QLabel()
        heartbeat_layout.addRow("启用心跳:", self.hb_enabled_label)
        self.hb_mode_label = QLabel()
        heartbeat_layout.addRow("心跳模式:", self.hb_mode_label)
        self.hb_interval_label = QLabel()
        heartbeat_layout.addRow("心跳间隔:", self.hb_interval_label)
        self.detail_tabs.addTab(heartbeat_widget, "心跳配置")

        detail_layout.addWidget(self.detail_tabs)
        layout.addWidget(detail_group)

    def refresh(self):
        self._populate_table()

    def set_endpoint_ids_filter(self, endpoint_ids: list[str]):
        self._filtered_endpoint_ids = endpoint_ids
        self._populate_table()
        if endpoint_ids:
            self.env_mode_label.setText(f"🔗 已过滤: {len(endpoint_ids)} 个端点的模板")
            self.env_mode_label.setStyleSheet(
                "padding:4px 12px; border-radius:4px; background:#1a2a3a; color:#89b4fa; font-weight:bold;")
        else:
            self.env_mode_label.setText("")

    def select_template(self, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for tpl in project.message_templates:
            if tpl.id == template_id:
                self._show_detail(tpl)
                break

    def _populate_table(self):
        project = self.project_manager.current_project
        self.template_table.setRowCount(0)
        if not project:
            return

        filter_cat = self.filter_combo.currentData()
        templates = project.message_templates

        if self._filtered_endpoint_ids:
            templates = [t for t in templates if t.endpoint_id in self._filtered_endpoint_ids or not t.endpoint_id]

        if filter_cat != "all" and not str(filter_cat).startswith("__sep_"):
            templates = [t for t in templates if t.category.value == filter_cat]

        for row, tpl in enumerate(templates):
            self.template_table.insertRow(row)
            self.template_table.setItem(row, 0, QTableWidgetItem(tpl.name))
            cat_label = CATEGORY_LABEL_MAP.get(tpl.category.value, tpl.category.value)
            self.template_table.setItem(row, 1, QTableWidgetItem(cat_label))
            self.template_table.setItem(row, 2, QTableWidgetItem(tpl.payload_type.value))
            self.template_table.setItem(row, 3, QTableWidgetItem(tpl.send_mode.value))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "primary")
            edit_btn.setFixedSize(78, 32)
            edit_btn.clicked.connect(lambda checked, tid=tpl.id: self.edit_template_requested.emit(tid))
            btn_layout.addWidget(edit_btn)

            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(78, 32)
            copy_btn.clicked.connect(lambda checked, tid=tpl.id: self._copy_template(tid))
            btn_layout.addWidget(copy_btn)

            del_btn = QPushButton("删除")
            del_btn.setProperty("class", "danger")
            del_btn.setFixedSize(78, 32)
            del_btn.clicked.connect(lambda checked, tid=tpl.id: self._delete_template(tid))
            btn_layout.addWidget(del_btn)

            self.template_table.setCellWidget(row, 4, btn_widget)

    def _show_detail(self, tpl: MessageTemplate):
        if tpl.payload_type == PayloadType.JSON:
            try:
                data = json.loads(tpl.content)
                self.detail_content.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                self.detail_content.setPlainText(tpl.content)
        else:
            self.detail_content.setPlainText(tpl.content)

        self.match_table.setRowCount(0)
        for row, rule in enumerate(tpl.match_rules):
            self.match_table.insertRow(row)
            self.match_table.setItem(row, 0, QTableWidgetItem(rule.path))
            self.match_table.setItem(row, 1, QTableWidgetItem(rule.operator.value))
            self.match_table.setItem(row, 2, QTableWidgetItem(rule.value))

        self.ack_enabled_label.setText("是" if tpl.ack_config.enabled else "否")
        self.ack_timeout_label.setText(f"{tpl.ack_config.timeout_ms} ms")
        self.ack_auto_label.setText("是" if tpl.ack_config.auto_reply else "否")

        self.resp_enabled_label.setText("是" if tpl.response_config.enabled else "否")
        self.resp_timeout_label.setText(f"{tpl.response_config.timeout_ms} ms")

        self.hb_enabled_label.setText("是" if tpl.heartbeat_config.enabled else "否")
        self.hb_mode_label.setText(tpl.heartbeat_config.mode.value)
        self.hb_interval_label.setText(f"{tpl.heartbeat_config.interval_ms} ms")

    def _new_template(self):
        from protocol_workbench.core.models import new_id
        project = self.project_manager.current_project
        if not project:
            return
        ep_id = self._filtered_endpoint_ids[0] if self._filtered_endpoint_ids else ""
        name, ok = QInputDialog.getText(self, "新建模板", "模板名称:", text="新模板")
        if ok and name:
            tpl = MessageTemplate(id=new_id(), name=name, endpoint_id=ep_id, content="{\n  \n}")
            project.message_templates.append(tpl)
            self.refresh()
            self.logger.info(f"新建模板: {name}")

    def _copy_template(self, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for tpl in project.message_templates:
            if tpl.id == template_id:
                from protocol_workbench.core.models import new_id
                new_tpl = MessageTemplate(id=new_id(), name=tpl.name + "_copy", endpoint_id=tpl.endpoint_id)
                new_tpl.category = tpl.category
                new_tpl.payload_type = tpl.payload_type
                new_tpl.content = tpl.content
                new_tpl.tree_nodes = copy.deepcopy(tpl.tree_nodes)
                new_tpl.send_mode = tpl.send_mode
                project.message_templates.append(new_tpl)
                self.refresh()
                self.logger.info(f"复制模板: {new_tpl.name}")
                break

    def _delete_template(self, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此模板吗？")
        if reply == QMessageBox.Yes:
            project.message_templates = [t for t in project.message_templates if t.id != template_id]
            self.refresh()

    def _filter_templates(self):
        self._populate_table()
