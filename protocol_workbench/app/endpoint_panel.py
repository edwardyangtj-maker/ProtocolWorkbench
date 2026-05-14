from __future__ import annotations

import asyncio
import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QFrame, QMessageBox, QScrollArea,
)

from protocol_workbench.core.models import (
    EndpointConfig, EndpointType, PayloadType, FrameMode,
    FrameRule, HeartbeatConfig, HeartbeatMode, FailAction,
    MessageTemplate, SendMode, AckConfig, ResponseConfig,
)
from protocol_workbench.core.runtime_manager import RuntimeManager
from protocol_workbench.core.project_manager import ProjectManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.core.template_engine import TemplateEngine


class EndpointPanel(QWidget):
    send_requested = Signal(str, str)

    def __init__(self, runtime: RuntimeManager, project_manager: ProjectManager,
                 logger: LoggerService, parent=None):
        super().__init__(parent)
        self.runtime = runtime
        self.project_manager = project_manager
        self.logger = logger
        self.current_endpoint: EndpointConfig | None = None
        self._rx_entries: list[dict[str, str]] = []
        self._rx_json_mode = "formatted"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()

        self.endpoint_combo = QComboBox()
        self.endpoint_combo.setMinimumWidth(200)
        self.endpoint_combo.currentIndexChanged.connect(self._on_endpoint_selected)
        top_layout.addWidget(QLabel("端点:"), 0)
        top_layout.addWidget(self.endpoint_combo, 1)

        self.start_btn = QPushButton("▶ 启动")
        self.start_btn.setProperty("class", "success")
        self.start_btn.clicked.connect(self._start_endpoint)
        top_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_endpoint)
        top_layout.addWidget(self.stop_btn)

        self.state_label = QLabel("⏸ 未启动")
        self.state_label.setProperty("class", "status_idle")
        top_layout.addWidget(self.state_label)

        self.env_mode_label = QLabel("")
        self.env_mode_label.setProperty("class", "status_idle")
        self.env_mode_label.setStyleSheet("padding:2px 8px; border-radius:4px;")
        top_layout.addWidget(self.env_mode_label)

        layout.addLayout(top_layout)

        content_splitter = QSplitter(Qt.Horizontal)

        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        basic_group = QGroupBox("基本配置")
        basic_form = QFormLayout()
        basic_group.setLayout(basic_form)

        self.name_edit = QLineEdit()
        basic_form.addRow("名称:", self.name_edit)

        self.type_combo = QComboBox()
        for t in EndpointType:
            self.type_combo.addItem(t.value, t.value)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        basic_form.addRow("类型:", self.type_combo)

        self.host_edit = QLineEdit("0.0.0.0")
        basic_form.addRow("本地IP:", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(0, 65535)
        self.port_spin.setValue(9000)
        self.port_spin.setSpecialValueText("自动分配")
        basic_form.addRow("本地端口:", self.port_spin)

        self.remote_host_edit = QLineEdit("127.0.0.1")
        basic_form.addRow("目标IP:", self.remote_host_edit)

        self.remote_port_spin = QSpinBox()
        self.remote_port_spin.setRange(1, 65535)
        self.remote_port_spin.setValue(9000)
        basic_form.addRow("目标端口:", self.remote_port_spin)

        self.path_edit = QLineEdit("/")
        basic_form.addRow("路径:", self.path_edit)

        self.http_method_combo = QComboBox()
        self.http_method_combo.addItem("POST", "POST")
        self.http_method_combo.addItem("GET", "GET")
        self.http_method_combo.addItem("PUT", "PUT")
        self.http_method_combo.addItem("DELETE", "DELETE")
        self.http_method_combo.addItem("PATCH", "PATCH")
        self.http_method_combo.addItem("HEAD", "HEAD")
        basic_form.addRow("HTTP方法:", self.http_method_combo)

        self.custom_headers_edit = QTextEdit()
        self.custom_headers_edit.setMaximumHeight(60)
        self.custom_headers_edit.setPlaceholderText('自定义Headers (JSON格式)\n如: {"Authorization": "Bearer xxx"}')
        basic_form.addRow("自定义Headers:", self.custom_headers_edit)

        self.reply_routes_group = QGroupBox("HTTP Server 自动回复路由")
        reply_layout = QVBoxLayout(self.reply_routes_group)
        self.reply_table = QTableWidget()
        self.reply_table.setColumnCount(5)
        self.reply_table.setHorizontalHeaderLabels(["方法", "路径", "状态码", "Content-Type", "响应体"])
        reply_header = self.reply_table.horizontalHeader()
        reply_header.setSectionResizeMode(0, QHeaderView.Fixed)
        reply_header.resizeSection(0, 70)
        reply_header.setSectionResizeMode(1, QHeaderView.Stretch)
        reply_header.setSectionResizeMode(2, QHeaderView.Fixed)
        reply_header.resizeSection(2, 60)
        reply_header.setSectionResizeMode(3, QHeaderView.Fixed)
        reply_header.resizeSection(3, 120)
        reply_header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.reply_table.setAlternatingRowColors(True)
        self.reply_table.setMaximumHeight(150)
        reply_layout.addWidget(self.reply_table)

        reply_btn_layout = QHBoxLayout()
        add_route_btn = QPushButton("➕ 添加路由")
        add_route_btn.clicked.connect(self._add_reply_route)
        reply_btn_layout.addWidget(add_route_btn)
        del_route_btn = QPushButton("🗑 删除路由")
        del_route_btn.clicked.connect(self._del_reply_route)
        reply_btn_layout.addWidget(del_route_btn)
        reply_btn_layout.addStretch()
        reply_layout.addLayout(reply_btn_layout)

        basic_form.addRow(self.reply_routes_group)

        config_layout.addWidget(basic_group)

        protocol_group = QGroupBox("协议配置")
        protocol_form = QFormLayout()
        protocol_group.setLayout(protocol_form)

        self.payload_combo = QComboBox()
        for p in PayloadType:
            self.payload_combo.addItem(p.value, p.value)
        protocol_form.addRow("Payload类型:", self.payload_combo)

        self.frame_combo = QComboBox()
        self.frame_combo.addItem("无 (Raw)", "")
        protocol_form.addRow("分帧规则:", self.frame_combo)

        self.connect_timeout_spin = QSpinBox()
        self.connect_timeout_spin.setRange(100, 60000)
        self.connect_timeout_spin.setValue(10000)
        self.connect_timeout_spin.setSuffix(" ms")
        protocol_form.addRow("连接超时:", self.connect_timeout_spin)

        self.read_timeout_spin = QSpinBox()
        self.read_timeout_spin.setRange(100, 300000)
        self.read_timeout_spin.setValue(30000)
        self.read_timeout_spin.setSuffix(" ms")
        protocol_form.addRow("读写超时:", self.read_timeout_spin)

        self.auto_reconnect_check = QCheckBox("自动重连")
        protocol_form.addRow("", self.auto_reconnect_check)

        config_layout.addWidget(protocol_group)

        heartbeat_group = QGroupBox("心跳配置")
        heartbeat_form = QFormLayout()
        heartbeat_group.setLayout(heartbeat_form)

        self.heartbeat_check = QCheckBox("启用心跳")
        heartbeat_form.addRow("", self.heartbeat_check)

        self.heartbeat_mode_combo = QComboBox()
        self.heartbeat_mode_combo.addItem("主动发送", "active")
        self.heartbeat_mode_combo.addItem("被动响应", "passive")
        heartbeat_form.addRow("模式:", self.heartbeat_mode_combo)

        self.heartbeat_interval_spin = QSpinBox()
        self.heartbeat_interval_spin.setRange(1000, 300000)
        self.heartbeat_interval_spin.setValue(30000)
        self.heartbeat_interval_spin.setSuffix(" ms")
        heartbeat_form.addRow("间隔:", self.heartbeat_interval_spin)

        self.heartbeat_timeout_spin = QSpinBox()
        self.heartbeat_timeout_spin.setRange(1000, 60000)
        self.heartbeat_timeout_spin.setValue(10000)
        self.heartbeat_timeout_spin.setSuffix(" ms")
        heartbeat_form.addRow("超时:", self.heartbeat_timeout_spin)

        self.heartbeat_fail_count_spin = QSpinBox()
        self.heartbeat_fail_count_spin.setRange(1, 100)
        self.heartbeat_fail_count_spin.setValue(3)
        heartbeat_form.addRow("最大失败次数:", self.heartbeat_fail_count_spin)

        self.heartbeat_fail_action_combo = QComboBox()
        for a in FailAction:
            self.heartbeat_fail_action_combo.addItem(a.value, a.value)
        heartbeat_form.addRow("失败动作:", self.heartbeat_fail_action_combo)

        config_layout.addWidget(heartbeat_group)

        self.save_config_btn = QPushButton("💾 保存配置")
        self.save_config_btn.setProperty("class", "primary")
        self.save_config_btn.clicked.connect(self._save_config)
        config_layout.addWidget(self.save_config_btn)

        config_layout.addStretch()
        config_scroll.setWidget(config_widget)

        content_splitter.addWidget(config_scroll)

        send_widget = QWidget()
        send_layout = QVBoxLayout(send_widget)

        send_group = QGroupBox("发送消息")
        send_inner = QVBoxLayout(send_group)
        send_inner.setSpacing(4)
        send_inner.setContentsMargins(8, 12, 8, 8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("模板:"))
        self.send_template_combo = QComboBox()
        self.send_template_combo.currentIndexChanged.connect(self._on_send_template_selected)
        row1.addWidget(self.send_template_combo, 3)
        row1.addWidget(QLabel("模式:"))
        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItem("只发送", SendMode.SEND_ONLY.value)
        self.send_mode_combo.addItem("只接收", SendMode.RECEIVE_ONLY.value)
        self.send_mode_combo.addItem("发送后等待Response", SendMode.SEND_WAIT_RESPONSE.value)
        self.send_mode_combo.addItem("接收后自动回复", SendMode.RECEIVE_AUTO_REPLY.value)
        row1.addWidget(self.send_mode_combo, 2)
        row1.addWidget(QLabel("目标:"))
        self.send_target_edit = QLineEdit()
        self.send_target_edit.setPlaceholderText("默认目标 / 广播")
        row1.addWidget(self.send_target_edit, 2)
        self.send_btn = QPushButton("📤 发送")
        self.send_btn.setProperty("class", "primary")
        self.send_btn.clicked.connect(self._send_message)
        row1.addWidget(self.send_btn)
        send_inner.addLayout(row1)

        self.raw_input = QTextEdit()
        self.raw_input.setMinimumHeight(200)
        self.raw_input.setPlaceholderText("输入原始发送内容...")
        send_inner.addWidget(self.raw_input)

        send_layout.addWidget(send_group)

        rx_group = QGroupBox("收发数据")
        rx_layout = QVBoxLayout(rx_group)
        self.rx_display = QTextEdit()
        self.rx_display.setReadOnly(True)
        self.rx_display.setMinimumHeight(250)
        rx_layout.addWidget(self.rx_display)
        rx_btn_layout = QHBoxLayout()

        self.format_rx_btn = QPushButton("格式化")
        self.format_rx_btn.setCheckable(True)
        self.format_rx_btn.setChecked(True)
        self.format_rx_btn.clicked.connect(lambda: self._set_rx_json_mode("formatted"))
        rx_btn_layout.addWidget(self.format_rx_btn)

        self.compress_rx_btn = QPushButton("压缩")
        self.compress_rx_btn.setCheckable(True)
        self.compress_rx_btn.clicked.connect(lambda: self._set_rx_json_mode("compressed"))
        rx_btn_layout.addWidget(self.compress_rx_btn)

        self.clear_rx_btn = QPushButton("清空")
        self.clear_rx_btn.clicked.connect(self._clear_rx_data)
        rx_btn_layout.addWidget(self.clear_rx_btn)
        rx_btn_layout.addStretch()
        self.rx_filter_label = QLabel("")
        self.rx_filter_label.setProperty("class", "subtitle")
        rx_btn_layout.addWidget(self.rx_filter_label)
        rx_layout.addLayout(rx_btn_layout)

        send_layout.addWidget(rx_group)
        send_layout.addStretch()

        content_splitter.addWidget(send_widget)
        content_splitter.setSizes([400, 600])

        layout.addWidget(content_splitter)

    def refresh(self):
        self.endpoint_combo.blockSignals(True)
        self.endpoint_combo.clear()
        project = self.project_manager.current_project
        if project:
            for ep in project.endpoints:
                self.endpoint_combo.addItem(ep.name, ep.id)

            self.frame_combo.blockSignals(True)
            self.frame_combo.clear()
            self.frame_combo.addItem("无 (Raw)", "")
            for fr in project.frame_rules:
                self.frame_combo.addItem(f"{fr.name} ({fr.mode.value})", fr.id)
            self.frame_combo.blockSignals(False)

            self.send_template_combo.blockSignals(True)
            self.send_template_combo.clear()
            for tpl in project.message_templates:
                self.send_template_combo.addItem(tpl.name, tpl.id)
            self.send_template_combo.blockSignals(False)

        self.endpoint_combo.blockSignals(False)

        if self.endpoint_combo.count() > 0:
            self._on_endpoint_selected(0)

    def select_endpoint(self, endpoint_id: str):
        for i in range(self.endpoint_combo.count()):
            if self.endpoint_combo.itemData(i) == endpoint_id:
                self.endpoint_combo.setCurrentIndex(i)
                break

    def set_environment_filter(self, env_name: str, endpoint_ids: list, mode: str):
        """根据环境过滤端点显示"""
        mode_label = "🟢 上位机模拟" if mode == "upper_computer" else "🔵 后端测试"
        self.env_mode_label.setText(mode_label)
        if mode == "upper_computer":
            self.env_mode_label.setStyleSheet(
                "padding:2px 8px; border-radius:4px; background:#1a3a2a; color:#a6e3a1; font-weight:bold;")
        else:
            self.env_mode_label.setStyleSheet(
                "padding:2px 8px; border-radius:4px; background:#1a2a3a; color:#89b4fa; font-weight:bold;")

        self.endpoint_combo.blockSignals(True)
        self.endpoint_combo.clear()
        project = self.project_manager.current_project
        if project:
            for ep in project.endpoints:
                if ep.id in endpoint_ids:
                    self.endpoint_combo.addItem(ep.name, ep.id)

            self.frame_combo.blockSignals(True)
            self.frame_combo.clear()
            self.frame_combo.addItem("无 (Raw)", "")
            for fr in project.frame_rules:
                self.frame_combo.addItem(f"{fr.name} ({fr.mode.value})", fr.id)
            self.frame_combo.blockSignals(False)

            self.send_template_combo.blockSignals(True)
            self.send_template_combo.clear()
            for tpl in project.message_templates:
                show = False
                if mode == "upper_computer":
                    show = tpl.category.value.startswith("report") or tpl.category.value in ("response", "ack", "heartbeat")
                else:
                    show = (tpl.category.value.startswith("cmd_") or
                            tpl.category.value.startswith("param_") or
                            tpl.category.value.startswith("query_"))
                if show:
                    self.send_template_combo.addItem(tpl.name, tpl.id)
            self.send_template_combo.blockSignals(False)

        self.endpoint_combo.blockSignals(False)

        if self.endpoint_combo.count() > 0:
            self._on_endpoint_selected(0)

    def update_endpoint_state(self, endpoint_id: str, state: str):
        if self.current_endpoint and self.current_endpoint.id == endpoint_id:
            state_map = {
                "idle": ("⏸ 未启动", "color: #a6adc8;"),
                "connecting": ("🔄 连接中...", "color: #f9e2af;"),
                "connected": ("🟢 已连接", "color: #a6e3a1;"),
                "listening": ("🟢 监听中", "color: #a6e3a1;"),
                "disconnected": ("🔴 已断开", "color: #f38ba8;"),
                "error": ("❌ 错误", "color: #f38ba8;"),
            }
            text, style = state_map.get(state, ("❓ 未知", "color: #a6adc8;"))
            self.state_label.setText(text)
            self.state_label.setStyleSheet(style)

    def _on_endpoint_selected(self, index: int):
        if index < 0:
            return
        ep_id = self.endpoint_combo.itemData(index)
        project = self.project_manager.current_project
        if not project:
            return
        for ep in project.endpoints:
            if ep.id == ep_id:
                self.current_endpoint = ep
                self._load_endpoint_config(ep)
                self.update_endpoint_state(ep.id, self.runtime.get_endpoint_state(ep.id))
                break

    def _load_endpoint_config(self, ep: EndpointConfig):
        self.name_edit.setText(ep.name)
        idx = self.type_combo.findData(ep.type.value)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.host_edit.setText(ep.host)
        self.port_spin.setValue(ep.port)
        self.remote_host_edit.setText(ep.remote_host)
        self.remote_port_spin.setValue(ep.remote_port)
        self.path_edit.setText(ep.path)
        idx = self.http_method_combo.findData(ep.http_method)
        if idx >= 0:
            self.http_method_combo.setCurrentIndex(idx)
        import json
        self.custom_headers_edit.setText(json.dumps(ep.custom_headers, ensure_ascii=False, indent=2) if ep.custom_headers else "")

        self.reply_table.setRowCount(0)
        for route in ep.reply_routes:
            row = self.reply_table.rowCount()
            self.reply_table.insertRow(row)
            method_combo = QComboBox()
            for m in ["*", "GET", "POST", "PUT", "DELETE", "PATCH"]:
                method_combo.addItem(m)
            idx = method_combo.findText(route.get("method", "*"))
            if idx >= 0:
                method_combo.setCurrentIndex(idx)
            self.reply_table.setCellWidget(row, 0, method_combo)
            self.reply_table.setItem(row, 1, QTableWidgetItem(route.get("path", "/*")))
            self.reply_table.setItem(row, 2, QTableWidgetItem(str(route.get("status", 200))))
            self.reply_table.setItem(row, 3, QTableWidgetItem(route.get("content_type", "application/json")))
            self.reply_table.setItem(row, 4, QTableWidgetItem(route.get("body", "{}")))

        idx = self.payload_combo.findData(ep.payload_type.value)
        if idx >= 0:
            self.payload_combo.setCurrentIndex(idx)

        idx = self.frame_combo.findData(ep.frame_rule_id)
        if idx >= 0:
            self.frame_combo.setCurrentIndex(idx)

        self.connect_timeout_spin.setValue(ep.connect_timeout_ms)
        self.read_timeout_spin.setValue(ep.read_timeout_ms)
        self.auto_reconnect_check.setChecked(ep.auto_reconnect)

        hc = ep.heartbeat_config
        self.heartbeat_check.setChecked(hc.enabled)
        idx = self.heartbeat_mode_combo.findData(hc.mode.value)
        if idx >= 0:
            self.heartbeat_mode_combo.setCurrentIndex(idx)
        self.heartbeat_interval_spin.setValue(hc.interval_ms)
        self.heartbeat_timeout_spin.setValue(hc.timeout_ms)
        self.heartbeat_fail_count_spin.setValue(hc.max_fail_count)
        idx = self.heartbeat_fail_action_combo.findData(hc.fail_action.value)
        if idx >= 0:
            self.heartbeat_fail_action_combo.setCurrentIndex(idx)

    def _save_config(self):
        if not self.current_endpoint:
            return
        ep = self.current_endpoint
        ep.name = self.name_edit.text()
        ep.type = EndpointType(self.type_combo.currentData())
        ep.host = self.host_edit.text()
        ep.port = self.port_spin.value()
        ep.remote_host = self.remote_host_edit.text()
        ep.remote_port = self.remote_port_spin.value()
        ep.path = self.path_edit.text()
        ep.http_method = self.http_method_combo.currentData() or "POST"
        import json
        try:
            headers_text = self.custom_headers_edit.toPlainText().strip()
            ep.custom_headers = json.loads(headers_text) if headers_text else {}
        except json.JSONDecodeError:
            ep.custom_headers = {}

        reply_routes = []
        for row in range(self.reply_table.rowCount()):
            method_widget = self.reply_table.cellWidget(row, 0)
            method = method_widget.currentText() if method_widget else "*"
            path_item = self.reply_table.item(row, 1)
            status_item = self.reply_table.item(row, 2)
            ct_item = self.reply_table.item(row, 3)
            body_item = self.reply_table.item(row, 4)
            reply_routes.append({
                "method": method,
                "path": path_item.text() if path_item else "/*",
                "status": int(status_item.text()) if status_item else 200,
                "content_type": ct_item.text() if ct_item else "application/json",
                "body": body_item.text() if body_item else "{}",
            })
        ep.reply_routes = reply_routes

        ep.payload_type = PayloadType(self.payload_combo.currentData())
        ep.frame_rule_id = self.frame_combo.currentData() or ""
        ep.connect_timeout_ms = self.connect_timeout_spin.value()
        ep.read_timeout_ms = self.read_timeout_spin.value()
        ep.auto_reconnect = self.auto_reconnect_check.isChecked()

        ep.heartbeat_config = HeartbeatConfig(
            enabled=self.heartbeat_check.isChecked(),
            mode=HeartbeatMode(self.heartbeat_mode_combo.currentData()),
            interval_ms=self.heartbeat_interval_spin.value(),
            timeout_ms=self.heartbeat_timeout_spin.value(),
            max_fail_count=self.heartbeat_fail_count_spin.value(),
            fail_action=FailAction(self.heartbeat_fail_action_combo.currentData()),
        )

        self.logger.info(f"端点配置已保存: {ep.name}")

    def _start_endpoint(self):
        if self.current_endpoint:
            self._save_config()
            asyncio.create_task(self.runtime.start_endpoint(self.current_endpoint))

    def _stop_endpoint(self):
        if self.current_endpoint:
            asyncio.create_task(self.runtime.stop_endpoint(self.current_endpoint.id))

    def _send_message(self):
        if not self.current_endpoint:
            return
        text = self.raw_input.toPlainText().strip()
        if not text:
            self.logger.warn("发送内容为空，请先选择消息模板")
            return
        ep_id = self.current_endpoint.id
        state = self.runtime.get_endpoint_state(ep_id)
        if state not in ("connected", "listening"):
            self.logger.error("端点未启动，请先启动端点")
            return
        try:
            rendered = self.runtime.template_engine.render_string(text)
            data = rendered.encode("utf-8")
            target = self.send_target_edit.text()

            display_text = rendered
            if self.current_endpoint.payload_type.value == "json":
                try:
                    import json
                    parsed = json.loads(rendered)
                    display_text = json.dumps(parsed, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            self.append_rx_data(f"{display_text}", self.current_endpoint.name, "TX")
            asyncio.create_task(self.runtime.send_raw(ep_id, data, target))
            self.logger.info(f"消息已发送: {len(data)} bytes")
        except Exception as e:
            self.logger.error(f"发送失败: {e}")

    def _on_send_template_selected(self, index: int):
        if index < 0:
            return
        tpl_id = self.send_template_combo.itemData(index)
        project = self.project_manager.current_project
        if not project:
            return
        for tpl in project.message_templates:
            if tpl.id == tpl_id:
                content = tpl.content
                if content:
                    try:
                        import json as _json
                        rendered = self.runtime.template_engine.render_string(content)
                        parsed = _json.loads(rendered)
                        self.raw_input.setPlainText(
                            _json.dumps(parsed, ensure_ascii=False, indent=2)
                        )
                    except Exception:
                        self.raw_input.setPlainText(content)
                else:
                    self.raw_input.setPlainText("")
                break

    def append_rx_data(self, text: str, endpoint_name: str = "", direction: str = "RX"):
        entry = {
            "text": text,
            "endpoint_name": endpoint_name,
            "direction": direction,
        }
        self._rx_entries.append(entry)
        self._append_rx_entry(entry)

    def _set_rx_json_mode(self, mode: str):
        if mode not in ("formatted", "compressed"):
            return
        self._rx_json_mode = mode

        self.format_rx_btn.blockSignals(True)
        self.compress_rx_btn.blockSignals(True)
        self.format_rx_btn.setChecked(mode == "formatted")
        self.compress_rx_btn.setChecked(mode == "compressed")
        self.format_rx_btn.blockSignals(False)
        self.compress_rx_btn.blockSignals(False)

        self._render_rx_data()

    def _clear_rx_data(self):
        self._rx_entries.clear()
        self.rx_display.clear()

    def _render_rx_data(self):
        self.rx_display.clear()
        for entry in self._rx_entries:
            self._append_rx_entry(entry, scroll_to_bottom=False)
        scrollbar = self.rx_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_rx_entry(self, entry: dict[str, str], scroll_to_bottom: bool = True):
        text = entry.get("text", "")
        endpoint_name = entry.get("endpoint_name", "")
        direction = entry.get("direction", "RX")

        import json as _json
        color_map = {"TX": "#89b4fa", "RX": "#a6e3a1"}
        color = color_map.get(direction, "#cdd6f4")
        prefix = f"[{direction}]"
        if endpoint_name:
            prefix = f"[{direction}][{endpoint_name}]"

        # 尝试解析 JSON，提取结构化信息用于可视化展示
        display_text = text
        try:
            parsed = _json.loads(self._extract_json_text(text))
            json_text = self._dump_rx_json(parsed)
            if isinstance(parsed, dict) and "header" in parsed and "body" in parsed:
                header = parsed.get("header", {})
                body = parsed.get("body", {})
                msg_type = header.get("msgType", "")
                msg_id = header.get("msgId", "")
                code = body.get("code", "")
                message = body.get("message", "")
                data = body.get("data", {})

                if msg_type == "response":
                    color = "#f9e2af"
                    info_parts = []
                    if msg_id:
                        info_parts.append(f"msgId={msg_id}")
                    if code:
                        info_parts.append(f"code={code}")
                    if message:
                        info_parts.append(f"message={message}")
                    info = " | ".join(info_parts) if info_parts else ""
                    summary = f"🟡 响应帧"
                    if info:
                        summary += f" [{info}]"
                    display_text = f"{summary}\n{json_text}"
                elif msg_type in ("command", "query", "parameter"):
                    color = "#89b4fa"
                    theme = body.get("theme", "")
                    info_parts = [f"msgType={msg_type}"]
                    if msg_id:
                        info_parts.append(f"msgId={msg_id}")
                    if theme:
                        info_parts.append(f"theme={theme}")
                    info = " | ".join(info_parts)
                    display_text = f"🔵 {info}\n{json_text}"
                elif msg_type == "report":
                    color = "#a6e3a1"
                    theme = body.get("theme", "")
                    info_parts = [f"msgType={msg_type}"]
                    if msg_id:
                        info_parts.append(f"msgId={msg_id}")
                    if theme:
                        info_parts.append(f"theme={theme}")
                    info = " | ".join(info_parts)
                    display_text = f"🟢 {info}\n{json_text}"
                else:
                    display_text = json_text
            else:
                display_text = json_text
        except (_json.JSONDecodeError, Exception):
            pass

        safe_prefix = html.escape(prefix)
        safe_text = html.escape(display_text)
        self.rx_display.append(
            f'<div style="margin-bottom:6px;">'
            f'<span style="color:{color}; font-weight:bold;">{safe_prefix}</span>'
            f'<pre style="white-space:pre-wrap; margin:2px 0 0 0; '
            f'font-family:Cascadia Code, Consolas, monospace; color:{color};">{safe_text}</pre>'
            f'</div>'
        )
        if scroll_to_bottom:
            scrollbar = self.rx_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _extract_json_text(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("*") and stripped.endswith("#"):
            return stripped[1:-1].strip()
        return stripped

    def _dump_rx_json(self, data) -> str:
        import json as _json
        if self._rx_json_mode == "compressed":
            return _json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return _json.dumps(data, ensure_ascii=False, indent=2)

    def _on_type_changed(self):
        ep_type = self.type_combo.currentData()
        is_http_client = ep_type == "http_client"
        is_http_server = ep_type == "http_server"
        is_ws = ep_type in ("websocket_client", "websocket_server")

        self.http_method_combo.setVisible(is_http_client)
        self.custom_headers_edit.setVisible(is_http_client or is_http_server)
        self.reply_routes_group.setVisible(is_http_server)
        self.path_edit.setVisible(is_http_client or is_http_server or is_ws)

        is_client = ep_type in ("tcp_client", "http_client", "websocket_client", "udp_endpoint")
        self.remote_host_edit.setVisible(is_client)
        self.remote_port_spin.setVisible(is_client)

        is_server = ep_type in ("tcp_server", "http_server", "websocket_server")
        self.host_edit.setVisible(is_server or not is_client)
        self.port_spin.setVisible(is_server or not is_client)

        # 客户端类型的本地端口设为0（自动分配），避免与监听端口冲突
        if is_client:
            if self.port_spin.value() != 0 and self.port_spin.value() >= 9000:
                self.port_spin.setValue(0)

        basic_form = self.http_method_combo.parent().layout()
        if basic_form:
            for i in range(basic_form.rowCount()):
                item = basic_form.itemAt(i, QFormLayout.LabelRole)
                field_item = basic_form.itemAt(i, QFormLayout.FieldRole)
                if field_item and field_item.widget():
                    widget = field_item.widget()
                    label_visible = widget.isVisible()
                    if item and item.widget():
                        item.widget().setVisible(label_visible)

    def _add_reply_route(self):
        row = self.reply_table.rowCount()
        self.reply_table.insertRow(row)
        method_combo = QComboBox()
        for m in ["*", "GET", "POST", "PUT", "DELETE", "PATCH"]:
            method_combo.addItem(m)
        self.reply_table.setCellWidget(row, 0, method_combo)
        self.reply_table.setItem(row, 1, QTableWidgetItem("/*"))
        self.reply_table.setItem(row, 2, QTableWidgetItem("200"))
        self.reply_table.setItem(row, 3, QTableWidgetItem("application/json"))
        self.reply_table.setItem(row, 4, QTableWidgetItem('{"status": "ok"}'))

    def _del_reply_route(self):
        row = self.reply_table.currentRow()
        if row >= 0:
            self.reply_table.removeRow(row)
