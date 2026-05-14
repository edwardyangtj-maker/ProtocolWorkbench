from __future__ import annotations

import json
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QTabWidget,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QMessageBox, QMenu, QApplication,
)

from protocol_workbench.core.logger_service import LoggerService


class LogPanel(QWidget):
    def __init__(self, logger: LoggerService, parent=None):
        super().__init__(parent)
        self.logger = logger
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部", "all")
        self.filter_combo.addItem("运行日志", "INFO")
        self.filter_combo.addItem("发送日志", "TX")
        self.filter_combo.addItem("接收日志", "RX")
        self.filter_combo.addItem("错误日志", "ERROR")
        self.filter_combo.addItem("调试日志", "DEBUG")
        toolbar.addWidget(QLabel("筛选:"), 0)
        toolbar.addWidget(self.filter_combo, 1)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(self.clear_btn)

        self.auto_scroll_check = QPushButton("自动滚动")
        self.auto_scroll_check.setCheckable(True)
        self.auto_scroll_check.setChecked(True)
        toolbar.addWidget(self.auto_scroll_check)

        toolbar.addStretch()

        self.count_label = QLabel("0 条")
        self.count_label.setProperty("class", "subtitle")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        self.log_tabs = QTabWidget()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Cascadia Code", 11))
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_tabs.addTab(self.log_text, "📝 运行日志")

        self.packet_table = QTableWidget()
        self.packet_table.setColumnCount(7)
        self.packet_table.setHorizontalHeaderLabels(["时间", "端点", "方向", "远端", "模板", "状态", "原始内容"])
        header = self.packet_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 100)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 40)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 60)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.packet_table.setAlternatingRowColors(True)
        self.packet_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.packet_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.packet_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packet_table.customContextMenuRequested.connect(self._on_packet_context_menu)
        self.log_tabs.addTab(self.packet_table, "📦 报文记录")

        layout.addWidget(self.log_tabs)

        self._log_count = 0
        self._packet_count = 0
        self._all_log_entries: list[tuple[str, str]] = []
        self._packet_records: list[dict] = []

    def _connect_signals(self):
        self.logger.log_signal.connect(self._on_log)
        self.logger.packet_signal.connect(self._on_packet)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)

    @Slot(str, str)
    def _on_log(self, level: str, message: str):
        self._all_log_entries.append((level, message))

        if not self._should_show_log(level):
            return

        color_map = {
            "DEBUG": "#a6adc8",
            "INFO": "#cdd6f4",
            "WARN": "#f9e2af",
            "ERROR": "#f38ba8",
            "TX": "#89b4fa",
            "RX": "#a6e3a1",
        }
        color = color_map.get(level, "#cdd6f4")

        self.log_text.append(f'<span style="color:{color}">{message}</span>')
        self._log_count += 1
        self.count_label.setText(f"{self._log_count} 条")

        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    @Slot(dict)
    def _on_packet(self, record: dict):
        self._packet_records.append(record)
        row = self.packet_table.rowCount()
        self.packet_table.insertRow(row)
        self.packet_table.setItem(row, 0, QTableWidgetItem(record.get("timestamp", "")[:19]))
        self.packet_table.setItem(row, 1, QTableWidgetItem(record.get("endpoint", "")))
        self.packet_table.setItem(row, 2, QTableWidgetItem(record.get("direction", "")))
        self.packet_table.setItem(row, 3, QTableWidgetItem(record.get("remote_addr", "")))
        self.packet_table.setItem(row, 4, QTableWidgetItem(record.get("template_name", "")))
        self.packet_table.setItem(row, 5, QTableWidgetItem(record.get("status", "")))

        raw_text = record.get("raw_text", "")
        display_text = raw_text[:80] + "..." if len(raw_text) > 80 else raw_text
        self.packet_table.setItem(row, 6, QTableWidgetItem(display_text))

        self._packet_count += 1

        if self.auto_scroll_check.isChecked():
            self.packet_table.scrollToBottom()

    def _clear_logs(self):
        self.log_text.clear()
        self.packet_table.setRowCount(0)
        self._log_count = 0
        self._packet_count = 0
        self._all_log_entries.clear()
        self.count_label.setText("0 条")

    def _apply_filter(self):
        filter_level = self.filter_combo.currentData()
        self.log_text.clear()
        self._log_count = 0

        color_map = {
            "DEBUG": "#a6adc8",
            "INFO": "#cdd6f4",
            "WARN": "#f9e2af",
            "ERROR": "#f38ba8",
            "TX": "#89b4fa",
            "RX": "#a6e3a1",
        }

        for level, message in self._all_log_entries:
            if filter_level != "all":
                priority = {"DEBUG": 0, "TX": 1, "RX": 1, "INFO": 2, "WARN": 3, "ERROR": 4}
                msg_priority = priority.get(level, 2)
                filter_priority = priority.get(filter_level, 2)
                if msg_priority < filter_priority:
                    continue

            color = color_map.get(level, "#cdd6f4")
            self.log_text.append(f'<span style="color:{color}">{message}</span>')
            self._log_count += 1

        self.count_label.setText(f"{self._log_count} 条")

    def _should_show_log(self, level: str) -> bool:
        filter_level = self.filter_combo.currentData()
        if filter_level == "all":
            return True
        priority = {"DEBUG": 0, "TX": 1, "RX": 1, "INFO": 2, "WARN": 3, "ERROR": 4}
        msg_priority = priority.get(level, 2)
        filter_priority = priority.get(filter_level, 2)
        return msg_priority >= filter_priority

    def _on_packet_context_menu(self, pos):
        row = self.packet_table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)

        view_action = menu.addAction("👁 查看详情")
        view_action.triggered.connect(lambda: self._view_packet_detail(row))

        compare_action = menu.addAction("🔍 对比选中两行")
        compare_action.triggered.connect(lambda: self._compare_packets())

        replay_action = menu.addAction("🔄 回放此报文")
        replay_action.triggered.connect(lambda: self._replay_packet(row))

        copy_action = menu.addAction("📋 复制原始内容")
        copy_action.triggered.connect(lambda: self._copy_packet_raw(row))

        menu.exec(self.packet_table.viewport().mapToGlobal(pos))

    def _view_packet_detail(self, row: int):
        if row < 0 or row >= len(self._packet_records):
            return
        record = self._packet_records[row]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"报文详情 - {record.get('endpoint', '')} {record.get('direction', '')}")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)

        info_layout = QFormLayout()
        info_layout.addRow("时间:", QLabel(record.get("timestamp", "")[:23]))
        info_layout.addRow("端点:", QLabel(record.get("endpoint", "")))
        info_layout.addRow("方向:", QLabel(record.get("direction", "")))
        info_layout.addRow("协议:", QLabel(record.get("protocol_type", "")))
        info_layout.addRow("远端:", QLabel(record.get("remote_addr", "")))
        info_layout.addRow("模板:", QLabel(record.get("template_name", "")))
        info_layout.addRow("状态:", QLabel(record.get("status", "")))
        layout.addLayout(info_layout)

        tab_widget = QTabWidget()

        raw_text_edit = QTextEdit()
        raw_text_edit.setReadOnly(True)
        raw_text_edit.setFont(QFont("Cascadia Code", 11))
        raw_text = record.get("raw_text", "")
        try:
            parsed = json.loads(raw_text)
            raw_text_edit.setText(json.dumps(parsed, ensure_ascii=False, indent=2))
        except (json.JSONDecodeError, TypeError):
            raw_text_edit.setText(raw_text)
        tab_widget.addTab(raw_text_edit, "📝 解析视图")

        hex_edit = QTextEdit()
        hex_edit.setReadOnly(True)
        hex_edit.setFont(QFont("Cascadia Code", 10))
        hex_text = record.get("raw_hex", "")
        if hex_text:
            formatted_hex = ""
            for i in range(0, len(hex_text), 2):
                if i > 0 and i % 32 == 0:
                    formatted_hex += "\n"
                elif i > 0 and i % 2 == 0:
                    formatted_hex += " "
                formatted_hex += hex_text[i:i+2]
            hex_edit.setText(formatted_hex)
        tab_widget.addTab(hex_edit, "🔢 Hex视图")

        json_edit = QTextEdit()
        json_edit.setReadOnly(True)
        json_edit.setFont(QFont("Cascadia Code", 11))
        parsed_json = record.get("parsed_json", "")
        if parsed_json:
            try:
                data = json.loads(parsed_json) if isinstance(parsed_json, str) else parsed_json
                json_edit.setText(json.dumps(data, ensure_ascii=False, indent=2))
            except (json.JSONDecodeError, TypeError):
                json_edit.setText(str(parsed_json))
        tab_widget.addTab(json_edit, "📋 JSON视图")

        layout.addWidget(tab_widget)

        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 复制原始内容")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(raw_text))
        btn_layout.addWidget(copy_btn)
        copy_hex_btn = QPushButton("📋 复制Hex")
        copy_hex_btn.clicked.connect(lambda: QApplication.clipboard().setText(hex_text))
        btn_layout.addWidget(copy_hex_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _compare_packets(self):
        rows = self.packet_table.selectionModel().selectedRows()
        if len(rows) < 2:
            QMessageBox.information(self, "提示", "请选择两行报文进行对比")
            return

        row1 = rows[0].row()
        row2 = rows[1].row()

        raw1_item = self.packet_table.item(row1, 6)
        raw2_item = self.packet_table.item(row2, 6)
        if not raw1_item or not raw2_item:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("报文对比")
        dialog.setMinimumSize(900, 500)
        layout = QVBoxLayout(dialog)

        splitter = QSplitter(Qt.Horizontal)

        left_edit = QTextEdit()
        left_edit.setReadOnly(True)
        left_edit.setFont(QFont("Cascadia Code", 10))
        raw1 = raw1_item.text()
        try:
            left_edit.setText(json.dumps(json.loads(raw1), ensure_ascii=False, indent=2))
        except (json.JSONDecodeError, TypeError):
            left_edit.setText(raw1)

        right_edit = QTextEdit()
        right_edit.setReadOnly(True)
        right_edit.setFont(QFont("Cascadia Code", 10))
        raw2 = raw2_item.text()
        try:
            right_edit.setText(json.dumps(json.loads(raw2), ensure_ascii=False, indent=2))
        except (json.JSONDecodeError, TypeError):
            right_edit.setText(raw2)

        splitter.addWidget(left_edit)
        splitter.addWidget(right_edit)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        dialog.exec()

    def _replay_packet(self, row: int):
        raw_item = self.packet_table.item(row, 6)
        direction_item = self.packet_table.item(row, 2)
        endpoint_item = self.packet_table.item(row, 1)
        if not raw_item or not endpoint_item:
            return
        if direction_item and direction_item.text() == "TX":
            QMessageBox.information(self, "提示", "只能回放接收到的报文")
            return

        endpoint_name = endpoint_item.text()
        raw_text = raw_item.text()

        app_window = self.window()
        if not hasattr(app_window, 'runtime_manager') or not hasattr(app_window, 'project_manager'):
            self.logger.error("无法访问运行时管理器")
            return

        project = app_window.project_manager.current_project
        if not project:
            self.logger.error("没有打开的项目")
            return

        endpoint_id = None
        for ep in project.endpoints:
            if ep.name == endpoint_name:
                endpoint_id = ep.id
                break

        if not endpoint_id:
            self.logger.error(f"未找到端点: {endpoint_name}")
            return

        state = app_window.runtime_manager.get_endpoint_state(endpoint_id)
        if state not in ("connected", "listening"):
            QMessageBox.warning(self, "警告", f"端点 '{endpoint_name}' 未启动，请先启动端点")
            return

        try:
            data = raw_text.encode("utf-8")
            import asyncio
            asyncio.create_task(app_window.runtime_manager.send_raw(endpoint_id, data))
            self.logger.info(f"回放报文已发送: {raw_text[:50]}...")
        except Exception as e:
            self.logger.error(f"回放报文发送失败: {e}")

    def _copy_packet_raw(self, row: int):
        raw_item = self.packet_table.item(row, 6)
        if raw_item:
            QApplication.clipboard().setText(raw_item.text())
