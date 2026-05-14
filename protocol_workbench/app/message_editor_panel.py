from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QComboBox, QLabel, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QTextEdit, QPlainTextEdit, QMenu, QInputDialog,
    QMessageBox, QFrame, QToolBar, QSpinBox, QLineEdit,
    QCheckBox,
)

from protocol_workbench.core.models import (
    MessageTemplate, JsonNode, JsonNodeType, PayloadType,
    TemplateCategory, SendMode, MatchRule, MatchOperator,
    AckConfig, ResponseConfig, HeartbeatConfig, HeartbeatMode, FailAction,
)
from protocol_workbench.core.template_engine import TemplateEngine
from protocol_workbench.core.variable_engine import VariableEngine
from protocol_workbench.core.logger_service import LoggerService


class JsonSourceEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = ""
            for ch in line:
                if ch in (" ", "\t"):
                    indent += ch
                else:
                    break
            stripped = line.rstrip()
            if stripped and stripped[-1] in ("{", "[", ":"):
                indent += "  "
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(indent)
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._formats = {}
        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor("#89b4fa"))
        self._formats["key"] = key_fmt

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#a6e3a1"))
        self._formats["string"] = string_fmt

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#fab387"))
        self._formats["number"] = number_fmt

        bool_fmt = QTextCharFormat()
        bool_fmt.setForeground(QColor("#f38ba8"))
        self._formats["bool"] = bool_fmt

        null_fmt = QTextCharFormat()
        null_fmt.setForeground(QColor("#a6adc8"))
        self._formats["null"] = null_fmt

        brace_fmt = QTextCharFormat()
        brace_fmt.setForeground(QColor("#f9e2af"))
        self._formats["brace"] = brace_fmt

    def highlightBlock(self, text: str):
        import re
        for m in re.finditer(r'"([^"\\]|\\.)*"\s*:', text):
            self.setFormat(m.start(), m.end() - m.start(), self._formats["key"])
        for m in re.finditer(r':\s*"([^"\\]|\\.)*"', text):
            start = text.index('"', m.start() + 1)
            self.setFormat(start, m.end() - start, self._formats["string"])
        for m in re.finditer(r':\s*(-?\d+\.?\d*)', text):
            self.setFormat(m.start() + 1, m.end() - m.start() - 1, self._formats["number"])
        for m in re.finditer(r':\s*(true|false)', text):
            self.setFormat(m.start() + 1, m.end() - m.start() - 1, self._formats["bool"])
        for m in re.finditer(r':\s*null', text):
            self.setFormat(m.start() + 1, m.end() - m.start() - 1, self._formats["null"])
        for m in re.finditer(r'[{}\[\],]', text):
            self.setFormat(m.start(), 1, self._formats["brace"])


class JsonTreeWidget(QTreeWidget):
    COL_KEY = 0
    COL_VALUE = 1
    COL_TYPE = 2
    COL_ENABLED = 3
    COL_DESC = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Key", "Value", "Type", "Enabled", "Description"])
        self.setColumnCount(5)
        header = self.header()
        header.setSectionResizeMode(self.COL_KEY, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_VALUE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_TYPE, 90)
        header.setSectionResizeMode(self.COL_ENABLED, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_ENABLED, 60)
        header.setSectionResizeMode(self.COL_DESC, QHeaderView.ResizeMode.Stretch)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        self.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.itemDoubleClicked.connect(self._on_double_clicked)

    def load_from_nodes(self, nodes: list[JsonNode]):
        self.clear()
        for node in nodes:
            item = self._create_item(node)
            self.addTopLevelItem(item)
        self.expandAll()

    def to_nodes(self) -> list[JsonNode]:
        nodes = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            nodes.append(self._item_to_node(item))
        return nodes

    def _create_item(self, node: JsonNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(self.COL_KEY, node.key)
        item.setText(self.COL_VALUE, node.value)
        item.setText(self.COL_TYPE, node.node_type.value)
        item.setCheckState(self.COL_ENABLED, Qt.Checked if node.enabled else Qt.Unchecked)
        item.setText(self.COL_DESC, node.description)
        item.setData(0, Qt.UserRole, node.node_type.value)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        for child in node.children:
            child_item = self._create_item(child)
            item.addChild(child_item)

        return item

    def _item_to_node(self, item: QTreeWidgetItem) -> JsonNode:
        node_type = JsonNodeType(item.text(self.COL_TYPE))
        children = []
        for i in range(item.childCount()):
            children.append(self._item_to_node(item.child(i)))
        return JsonNode(
            key=item.text(self.COL_KEY),
            value=item.text(self.COL_VALUE),
            node_type=node_type,
            enabled=item.checkState(self.COL_ENABLED) == Qt.Checked,
            description=item.text(self.COL_DESC),
            children=children,
        )

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)

        add_child_action = menu.addAction("➕ 添加子节点")
        add_child_action.triggered.connect(lambda: self._add_child(item))

        if item:
            add_sibling_action = menu.addAction("➕ 添加兄弟节点")
            add_sibling_action.triggered.connect(lambda: self._add_sibling(item))

            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_item(item))

            menu.addSeparator()
            copy_action = menu.addAction("📋 复制节点")
            copy_action.triggered.connect(lambda: self._copy_item(item))

        menu.exec(self.viewport().mapToGlobal(pos))

    def _add_child(self, parent: QTreeWidgetItem | None):
        node = JsonNode(key="new_key", value="", node_type=JsonNodeType.STRING)
        new_item = self._create_item(node)
        if parent:
            parent.addChild(new_item)
            parent.setExpanded(True)
        else:
            self.addTopLevelItem(new_item)

    def _add_sibling(self, item: QTreeWidgetItem):
        node = JsonNode(key="new_key", value="", node_type=JsonNodeType.STRING)
        new_item = self._create_item(node)
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            parent.insertChild(idx + 1, new_item)
        else:
            idx = self.indexOfTopLevelItem(item)
            self.insertTopLevelItem(idx + 1, new_item)

    def _delete_item(self, item: QTreeWidgetItem):
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            idx = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(idx)

    def _copy_item(self, item: QTreeWidgetItem):
        node = self._item_to_node(item)
        node.key = node.key + "_copy"
        new_item = self._create_item(node)
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            parent.insertChild(idx + 1, new_item)
        else:
            idx = self.indexOfTopLevelItem(item)
            self.insertTopLevelItem(idx + 1, new_item)

    def _on_double_clicked(self, item: QTreeWidgetItem, column: int):
        if column == self.COL_TYPE:
            current_type = item.text(self.COL_TYPE)
            types = [t.value for t in JsonNodeType]
            current_idx = types.index(current_type) if current_type in types else 0
            from PySide6.QtWidgets import QComboBox
            combo = QComboBox()
            for t in JsonNodeType:
                combo.addItem(t.value, t.value)
            combo.setCurrentIndex(current_idx)

            def on_type_selected(idx, itm=item, cb=combo):
                self._update_item_type(itm, cb.currentData())

            combo.currentIndexChanged.connect(on_type_selected)
            combo.setFocusPolicy(Qt.StrongFocus)
            self.setItemWidget(item, column, combo)
            combo.showPopup()
        elif column == self.COL_ENABLED:
            new_state = Qt.Unchecked if item.checkState(column) == Qt.Checked else Qt.Checked
            item.setCheckState(column, new_state)
        elif column in (self.COL_KEY, self.COL_VALUE, self.COL_DESC):
            self.editItem(item, column)

    def _update_item_type(self, item: QTreeWidgetItem, type_value: str):
        item.setText(self.COL_TYPE, type_value)
        item.setData(0, Qt.UserRole, type_value)
        self.removeItemWidget(item, self.COL_TYPE)


class MessageEditorPanel(QWidget):
    template_saved = Signal()
    quick_send_requested = Signal(str, str)

    def __init__(self, template_engine: TemplateEngine, variable_engine: VariableEngine,
                 logger: LoggerService, project_manager=None, parent=None):
        super().__init__(parent)
        self.template_engine = template_engine
        self.variable_engine = variable_engine
        self.logger = logger
        self.project_manager = project_manager
        self.current_template: MessageTemplate | None = None
        self._setup_ui()
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()

        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(200)
        top_layout.addWidget(QLabel("模板:"), 0)
        top_layout.addWidget(self.template_combo, 1)

        self.new_btn = QPushButton("+ 新建")
        self.new_btn.clicked.connect(self._new_template)
        top_layout.addWidget(self.new_btn)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.clicked.connect(self._save_template)
        top_layout.addWidget(self.save_btn)

        layout.addLayout(top_layout)

        info_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("模板名称")
        info_layout.addWidget(QLabel("名称:"), 0)
        info_layout.addWidget(self.name_edit, 2)

        self.category_combo = QComboBox()
        for c in TemplateCategory:
            self.category_combo.addItem(c.value, c.value)
        info_layout.addWidget(QLabel("分类:"), 0)
        info_layout.addWidget(self.category_combo, 1)

        self.payload_combo = QComboBox()
        for p in PayloadType:
            self.payload_combo.addItem(p.value, p.value)
        info_layout.addWidget(QLabel("Payload:"), 0)
        info_layout.addWidget(self.payload_combo, 1)

        layout.addLayout(info_layout)

        self.editor_tabs = QTabWidget()

        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)

        source_toolbar = QHBoxLayout()
        self.format_btn = QPushButton("格式化")
        self.format_btn.clicked.connect(self._format_json)
        source_toolbar.addWidget(self.format_btn)

        self.compress_btn = QPushButton("压缩")
        self.compress_btn.clicked.connect(self._compress_json)
        source_toolbar.addWidget(self.compress_btn)

        self.validate_btn = QPushButton("校验")
        self.validate_btn.clicked.connect(self._validate_json)
        source_toolbar.addWidget(self.validate_btn)

        self.sync_to_tree_btn = QPushButton("同步到树形 →")
        self.sync_to_tree_btn.setProperty("class", "primary")
        self.sync_to_tree_btn.clicked.connect(self._sync_to_tree)
        source_toolbar.addWidget(self.sync_to_tree_btn)

        source_toolbar.addStretch()
        source_layout.addLayout(source_toolbar)

        self.source_edit = JsonSourceEdit()
        self.source_edit.setFont(QFont("Cascadia Code", 11))
        self.highlighter = JsonHighlighter(self.source_edit.document())
        source_layout.addWidget(self.source_edit)

        self.json_error_label = QLabel("")
        self.json_error_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
        source_layout.addWidget(self.json_error_label)

        self.editor_tabs.addTab(source_widget, "📝 源码模式")

        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_toolbar = QHBoxLayout()
        self.sync_to_source_btn = QPushButton("← 同步到源码")
        self.sync_to_source_btn.setProperty("class", "primary")
        self.sync_to_source_btn.clicked.connect(self._sync_to_source)
        tree_toolbar.addWidget(self.sync_to_source_btn)

        self.add_root_btn = QPushButton("+ 添加根节点")
        self.add_root_btn.clicked.connect(self._add_root_node)
        tree_toolbar.addWidget(self.add_root_btn)

        tree_toolbar.addStretch()
        tree_layout.addLayout(tree_toolbar)

        self.json_tree = JsonTreeWidget()
        tree_layout.addWidget(self.json_tree)

        self.editor_tabs.addTab(tree_widget, "🌳 树形模式")

        layout.addWidget(self.editor_tabs)

        send_layout = QHBoxLayout()
        self.send_mode_combo = QComboBox()
        for s in SendMode:
            self.send_mode_combo.addItem(s.value, s.value)
        send_layout.addWidget(QLabel("发送模式:"), 0)
        send_layout.addWidget(self.send_mode_combo, 1)

        self.endpoint_combo = QComboBox()
        send_layout.addWidget(QLabel("端点:"), 0)
        send_layout.addWidget(self.endpoint_combo, 1)

        self.quick_send_btn = QPushButton("📤 快速发送")
        self.quick_send_btn.setProperty("class", "primary")
        self.quick_send_btn.clicked.connect(self._quick_send)
        send_layout.addWidget(self.quick_send_btn)

        layout.addLayout(send_layout)

    def load_template(self, template: MessageTemplate):
        self.current_template = template
        self.name_edit.setText(template.name)
        idx = self.category_combo.findData(template.category.value)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        idx = self.payload_combo.findData(template.payload_type.value)
        if idx >= 0:
            self.payload_combo.setCurrentIndex(idx)

        self.source_edit.setPlainText(template.content)
        self.json_error_label.setText("")

        if template.tree_nodes:
            self.json_tree.load_from_nodes(template.tree_nodes)
        elif template.content:
            self._sync_to_tree()

        idx = self.send_mode_combo.findData(template.send_mode.value)
        if idx >= 0:
            self.send_mode_combo.setCurrentIndex(idx)

    def refresh(self):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        project = self._get_project()
        if project:
            for tpl in project.message_templates:
                self.template_combo.addItem(tpl.name, tpl.id)

            self.endpoint_combo.blockSignals(True)
            self.endpoint_combo.clear()
            for ep in project.endpoints:
                self.endpoint_combo.addItem(ep.name, ep.id)
            self.endpoint_combo.blockSignals(False)

        current_id = self.current_template.id if self.current_template else None
        if current_id:
            for i in range(self.template_combo.count()):
                if self.template_combo.itemData(i) == current_id:
                    self.template_combo.setCurrentIndex(i)
                    break
        elif self.template_combo.count() > 0:
            self._on_template_selected(0)

        self.template_combo.blockSignals(False)

    def _on_template_selected(self, index: int):
        if index < 0:
            return
        tpl_id = self.template_combo.itemData(index)
        project = self._get_project()
        if project:
            for tpl in project.message_templates:
                if tpl.id == tpl_id:
                    self.load_template(tpl)
                    break

    def _new_template(self):
        from protocol_workbench.core.models import new_id
        project = self._get_project()
        if not project:
            return
        name, ok = QInputDialog.getText(self, "新建模板", "模板名称:", text="新模板")
        if ok and name:
            tpl = MessageTemplate(id=new_id(), name=name, content="{\n  \n}")
            project.message_templates.append(tpl)
            self.load_template(tpl)
            self.refresh()
            self.logger.info(f"新建模板: {name}")

    def _save_template(self):
        if not self.current_template:
            return
        tpl = self.current_template
        tpl.name = self.name_edit.text()
        tpl.category = TemplateCategory(self.category_combo.currentData())
        tpl.payload_type = PayloadType(self.payload_combo.currentData())
        tpl.content = self.source_edit.toPlainText()
        tpl.tree_nodes = self.json_tree.to_nodes()
        tpl.send_mode = SendMode(self.send_mode_combo.currentData())

        self.template_saved.emit()
        self.refresh()
        self.logger.info(f"模板已保存: {tpl.name}")

    def _format_json(self):
        text = self.source_edit.toPlainText()
        try:
            data = json.loads(text)
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            self.source_edit.setPlainText(formatted)
            self.json_error_label.setText("")
        except json.JSONDecodeError as e:
            self.json_error_label.setText(f"JSON格式错误: 行{e.lineno} 列{e.colno} - {e.msg}")

    def _compress_json(self):
        text = self.source_edit.toPlainText()
        try:
            data = json.loads(text)
            compressed = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            self.source_edit.setPlainText(compressed)
            self.json_error_label.setText("")
        except json.JSONDecodeError as e:
            self.json_error_label.setText(f"JSON格式错误: 行{e.lineno} 列{e.colno} - {e.msg}")

    def _validate_json(self):
        text = self.source_edit.toPlainText()
        try:
            json.loads(text)
            self.json_error_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            self.json_error_label.setText("✓ JSON格式正确")
        except json.JSONDecodeError as e:
            self.json_error_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
            self.json_error_label.setText(f"✗ JSON格式错误: 行{e.lineno} 列{e.colno} - {e.msg}")

    def _sync_to_tree(self):
        text = self.source_edit.toPlainText()
        try:
            data = json.loads(text)
            nodes = TemplateEngine.json_to_tree_nodes(data)
            self.json_tree.load_from_nodes(nodes)
            self.json_error_label.setText("")
        except json.JSONDecodeError as e:
            self.json_error_label.setText(f"无法同步: JSON格式错误 - {e.msg}")

    def _sync_to_source(self):
        nodes = self.json_tree.to_nodes()
        json_str = TemplateEngine.tree_nodes_to_json(nodes)
        self.source_edit.setPlainText(json_str)

    def _add_root_node(self):
        node = JsonNode(key="new_key", value="", node_type=JsonNodeType.STRING)
        item = self.json_tree._create_item(node)
        self.json_tree.addTopLevelItem(item)

    def _get_project(self):
        if self.project_manager:
            return self.project_manager.current_project
        return None

    def _quick_send(self):
        if not self.current_template:
            self.logger.warn("请先选择或新建模板")
            return
        ep_id = self.endpoint_combo.currentData()
        if not ep_id:
            self.logger.warn("请先选择发送端点")
            return
        self._save_template()
        self.quick_send_requested.emit(ep_id, self.current_template.id)
        self.logger.info(f"快速发送: {self.current_template.name} -> {ep_id}")
