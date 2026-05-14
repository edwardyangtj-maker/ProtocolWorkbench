from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QInputDialog, QMessageBox,
    QHeaderView, QToolBar, QFrame, QDialog, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QSpinBox,
    QTextEdit, QTabWidget, QDialogButtonBox,
)

from protocol_workbench.core.project_manager import ProjectManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.core.models import (
    Project, Environment, EndpointConfig, EndpointType,
    MessageTemplate, Scenario, FrameRule, TemplateCategory,
)


class ProjectPanel(QWidget):
    project_changed = Signal()
    endpoint_selected = Signal(str)
    template_selected = Signal(str)
    scenario_selected = Signal(str)
    environment_selected = Signal(str)
    environment_start_requested = Signal(str)
    environment_stop_requested = Signal(str)

    def __init__(self, project_manager: ProjectManager, logger: LoggerService, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.logger = logger
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setProperty("class", "card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.project_name_label = QLabel("项目: 未创建")
        self.project_name_label.setProperty("class", "title")
        header_layout.addWidget(self.project_name_label)

        self.project_desc_label = QLabel("")
        self.project_desc_label.setProperty("class", "subtitle")
        header_layout.addWidget(self.project_desc_label)

        layout.addWidget(header)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 4, 8, 4)

        self.add_env_btn = QPushButton("+ 环境")
        self.add_env_btn.setFixedHeight(28)
        self.add_env_btn.clicked.connect(self._add_environment)
        btn_layout.addWidget(self.add_env_btn)

        self.add_ep_btn = QPushButton("+ 端点")
        self.add_ep_btn.setFixedHeight(28)
        self.add_ep_btn.clicked.connect(self._add_endpoint)
        btn_layout.addWidget(self.add_ep_btn)

        self.add_tpl_btn = QPushButton("+ 模板")
        self.add_tpl_btn.setFixedHeight(28)
        self.add_tpl_btn.clicked.connect(self._add_template)
        btn_layout.addWidget(self.add_tpl_btn)

        layout.addLayout(btn_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        layout.addWidget(self.tree)

    def refresh(self):
        self.tree.clear()
        project = self.project_manager.current_project
        if not project:
            self.project_name_label.setText("项目: 未创建")
            self.project_desc_label.setText("")
            return

        self.project_name_label.setText(f"项目: {project.name}")
        self.project_desc_label.setText(project.description or "双击编辑项目信息")

        root = QTreeWidgetItem(self.tree, [f"📦 {project.name}"])
        root.setData(0, Qt.UserRole, ("project", project.id))
        root.setExpanded(True)

        env_root = QTreeWidgetItem(root, ["🌐 环境"])
        env_root.setData(0, Qt.UserRole, ("env_root", ""))
        env_root.setExpanded(True)

        for env in project.environments:
            env_item = QTreeWidgetItem(env_root, [f"🏠 {env.name}"])
            env_item.setData(0, Qt.UserRole, ("environment", env.id))
            env_item.setExpanded(False)

            for ep_id in env.endpoint_ids:
                for ep in project.endpoints:
                    if ep.id == ep_id:
                        icon = self._endpoint_icon(ep.type)
                        ep_item = QTreeWidgetItem(env_item, [f"{icon} {ep.name}"])
                        ep_item.setData(0, Qt.UserRole, ("endpoint", ep.id, ep.name))

        ep_root = QTreeWidgetItem(root, ["📡 端点"])
        ep_root.setData(0, Qt.UserRole, ("ep_root", ""))
        ep_root.setExpanded(True)

        for ep in project.endpoints:
            icon = self._endpoint_icon(ep.type)
            ep_item = QTreeWidgetItem(ep_root, [f"{icon} {ep.name}"])
            ep_item.setData(0, Qt.UserRole, ("endpoint", ep.id, ep.name))

        tpl_root = QTreeWidgetItem(root, ["📋 模板"])
        tpl_root.setData(0, Qt.UserRole, ("tpl_root", ""))
        tpl_root.setExpanded(True)

        categories = {}
        for tpl in project.message_templates:
            cat = tpl.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tpl)

        for cat, templates in categories.items():
            cat_label = self._category_label(cat)
            cat_item = QTreeWidgetItem(tpl_root, [cat_label])
            cat_item.setData(0, Qt.UserRole, ("category", cat))
            for tpl in templates:
                tpl_item = QTreeWidgetItem(cat_item, [f"📄 {tpl.name}"])
                tpl_item.setData(0, Qt.UserRole, ("template", tpl.id))

        scenario_root = QTreeWidgetItem(root, ["🎬 场景"])
        scenario_root.setData(0, Qt.UserRole, ("scenario_root", ""))
        for sc in project.scenarios:
            sc_item = QTreeWidgetItem(scenario_root, [f"🎞 {sc.name}"])
            sc_item.setData(0, Qt.UserRole, ("scenario", sc.id))

        frame_root = QTreeWidgetItem(root, ["🔧 分帧规则"])
        frame_root.setData(0, Qt.UserRole, ("frame_root", ""))
        for fr in project.frame_rules:
            fr_item = QTreeWidgetItem(frame_root, [f"📏 {fr.name} ({fr.mode.value})"])
            fr_item.setData(0, Qt.UserRole, ("frame_rule", fr.id))

        self.tree.expandAll()

    def update_endpoint_state(self, endpoint_id: str, state: str):
        state_icons = {
            "idle": "⏸",
            "connecting": "🔄",
            "connected": "🟢",
            "listening": "🟢",
            "disconnected": "🔴",
            "error": "❌",
        }
        state_icon = state_icons.get(state, "⏸")

        def _update_item_recursive(item: QTreeWidgetItem):
            data = item.data(0, Qt.UserRole)
            if data and len(data) >= 2 and data[0] == "endpoint" and data[1] == endpoint_id:
                ep_name = data[2] if len(data) >= 3 else ""
                if not ep_name:
                    project = self.project_manager.current_project
                    if project:
                        for ep in project.endpoints:
                            if ep.id == endpoint_id:
                                ep_name = ep.name
                                break
                ep_type_icon = ""
                project = self.project_manager.current_project
                if project:
                    for ep in project.endpoints:
                        if ep.id == endpoint_id:
                            ep_type_icon = self._endpoint_icon(ep.type)
                            break
                item.setText(0, f"{state_icon} {ep_type_icon} {ep_name}")
            for i in range(item.childCount()):
                _update_item_recursive(item.child(i))

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            _update_item_recursive(root.child(i))

    def _endpoint_icon(self, ep_type: EndpointType) -> str:
        icons = {
            EndpointType.TCP_CLIENT: "🔌",
            EndpointType.TCP_SERVER: "🖥",
            EndpointType.HTTP_CLIENT: "🌐",
            EndpointType.HTTP_SERVER: "🖥",
            EndpointType.UDP_ENDPOINT: "📡",
            EndpointType.WS_CLIENT: "🔌",
            EndpointType.WS_SERVER: "🖥",
        }
        return icons.get(ep_type, "📡")

    def _category_label(self, cat: str) -> str:
        labels = {
            "message": "📨 消息",
            "cmd_laser": "⚙ 激光器",
            "cmd_camera": "⚙ 相机",
            "cmd_range": "⚙ 测距",
            "cmd_turntable": "⚙ 转台",
            "cmd_power": "⚙ 上下电",
            "cmd_connect": "⚙ 连接",
            "param_scan_config": "⚙ 扫描配置",
            "param_monitor_point": "⚙ 测距点",
            "param_range_param": "⚙ 测距参数",
            "param_imaging_param": "⚙ 成像参数",
            "param_camera_param": "⚙ 相机参数",
            "param_fan_param": "⚙ 风扇参数",
            "query_component": "🔍 组件查询",
            "query_range_config": "🔍 测距查询",
            "query_camera_calib": "🔍 标定查询",
            "report_device_status": "📊 设备状态",
            "report_alarm": "📊 告警",
            "report_img": "📊 成像",
            "report_high_range": "📊 高精度测距",
            "report_range_result": "📊 测距结果",
            "report_task": "📊 任务",
            "response": "↩ 响应",
            "ack": "✅ ACK",
            "heartbeat": "💓 心跳",
            "http_request": "🌐 HTTP请求",
            "ws_message": "🔌 WS消息",
            "udp_message": "📡 UDP消息",
            "tcp_message": "🔌 TCP消息",
        }
        return labels.get(cat, f"📄 {cat}")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        kind = data[0]
        obj_id = data[1]
        if kind == "endpoint":
            self.endpoint_selected.emit(obj_id)
        elif kind == "template":
            self.template_selected.emit(obj_id)
        elif kind == "scenario":
            self.scenario_selected.emit(obj_id)
        elif kind == "environment":
            self.environment_selected.emit(obj_id)
        elif kind == "project":
            self._edit_project_info()

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        kind = data[0]
        obj_id = data[1]
        menu = QMenu(self)

        if kind == "environment":
            activate_action = menu.addAction("▶ 切换到该环境")
            activate_action.triggered.connect(lambda: self.environment_selected.emit(obj_id))
            menu.addSeparator()
            start_action = menu.addAction("▶ 启动环境")
            start_action.triggered.connect(lambda: self.environment_start_requested.emit(obj_id))
            stop_action = menu.addAction("⏹ 停止环境")
            stop_action.triggered.connect(lambda: self.environment_stop_requested.emit(obj_id))
            menu.addSeparator()
            add_ep_action = menu.addAction("➕ 添加端点到环境")
            add_ep_action.triggered.connect(lambda: self._add_endpoint_to_environment(obj_id))
            manage_vars_action = menu.addAction("🔧 管理环境变量")
            manage_vars_action.triggered.connect(lambda: self._manage_environment_variables(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_environment(obj_id))
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_environment(obj_id))

        elif kind == "endpoint":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.endpoint_selected.emit(obj_id))
            menu.addSeparator()
            add_to_env_menu = menu.addMenu("📋 添加到环境")
            project = self.project_manager.current_project
            if project:
                for env in project.environments:
                    env_action = add_to_env_menu.addAction(env.name)
                    env_action.triggered.connect(lambda checked, eid=obj_id, envid=env.id: self._add_ep_to_env(eid, envid))
            menu.addSeparator()
            remove_from_env_menu = menu.addMenu("📋 从环境移除")
            if project:
                for env in project.environments:
                    if obj_id in env.endpoint_ids:
                        env_action = remove_from_env_menu.addAction(env.name)
                        env_action.triggered.connect(lambda checked, eid=obj_id, envid=env.id: self._remove_ep_from_env(eid, envid))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_endpoint(obj_id))

        elif kind == "template":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.template_selected.emit(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_template(obj_id))

        elif kind == "scenario":
            run_action = menu.addAction("▶ 运行场景")
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.scenario_selected.emit(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_scenario(obj_id))

        elif kind == "frame_rule":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self._edit_frame_rule(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_frame_rule(obj_id))

        elif kind == "frame_root":
            add_action = menu.addAction("➕ 新建分帧规则")
            add_action.triggered.connect(self._add_frame_rule)

        elif kind == "env_root":
            add_action = menu.addAction("➕ 新建环境")
            add_action.triggered.connect(self._add_environment)

        elif kind == "ep_root":
            add_action = menu.addAction("➕ 新建端点")
            add_action.triggered.connect(self._add_endpoint)

        elif kind == "tpl_root":
            add_action = menu.addAction("➕ 新建模板")
            add_action.triggered.connect(self._add_template)

        elif kind == "scenario_root":
            add_action = menu.addAction("➕ 新建场景")
            add_action.triggered.connect(self._add_scenario)

        elif kind == "project":
            edit_action = menu.addAction("✏ 编辑项目信息")
            edit_action.triggered.connect(self._edit_project_info)
            menu.addSeparator()
            save_action = menu.addAction("💾 保存项目")
            save_action.triggered.connect(self._save_project)

        elif kind == "category":
            add_action = menu.addAction("➕ 新建模板")
            add_action.triggered.connect(self._add_template)

        elif kind == "frame_rule":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self._edit_frame_rule(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_frame_rule(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_frame_rule(obj_id))

        elif kind == "environment":
            start_action = menu.addAction("▶ 启动环境")
            start_action.triggered.connect(lambda: self.environment_start_requested.emit(obj_id))
            stop_action = menu.addAction("⏹ 停止环境")
            stop_action.triggered.connect(lambda: self.environment_stop_requested.emit(obj_id))
            menu.addSeparator()
            add_ep_action = menu.addAction("➕ 添加端点到环境")
            add_ep_action.triggered.connect(lambda: self._add_endpoint_to_environment(obj_id))
            manage_vars_action = menu.addAction("🔧 管理环境变量")
            manage_vars_action.triggered.connect(lambda: self._manage_environment_variables(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_environment(obj_id))
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_environment(obj_id))

        elif kind == "endpoint":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.endpoint_selected.emit(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_endpoint(obj_id))
            menu.addSeparator()
            add_to_env_menu = menu.addMenu("📋 添加到环境")
            project = self.project_manager.current_project
            if project:
                for env in project.environments:
                    env_action = add_to_env_menu.addAction(env.name)
                    env_action.triggered.connect(lambda checked, eid=obj_id, envid=env.id: self._add_ep_to_env(eid, envid))
            menu.addSeparator()
            remove_from_env_menu = menu.addMenu("📋 从环境移除")
            if project:
                for env in project.environments:
                    if obj_id in env.endpoint_ids:
                        env_action = remove_from_env_menu.addAction(env.name)
                        env_action.triggered.connect(lambda checked, eid=obj_id, envid=env.id: self._remove_ep_from_env(eid, envid))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_endpoint(obj_id))

        elif kind == "template":
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.template_selected.emit(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_template(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_template(obj_id))

        elif kind == "scenario":
            run_action = menu.addAction("▶ 运行场景")
            edit_action = menu.addAction("✏ 编辑")
            edit_action.triggered.connect(lambda: self.scenario_selected.emit(obj_id))
            menu.addSeparator()
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._rename_scenario(obj_id))
            menu.addSeparator()
            delete_action = menu.addAction("🗑 删除")
            delete_action.triggered.connect(lambda: self._delete_scenario(obj_id))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _add_environment(self):
        name, ok = QInputDialog.getText(self, "新建环境", "环境名称:", text="新环境")
        if ok and name:
            from protocol_workbench.core.models import new_id
            env = Environment(id=new_id(), name=name)
            self.project_manager.current_project.environments.append(env)
            self.project_changed.emit()
            self.logger.info(f"新建环境: {name}")

    def _add_endpoint(self):
        from protocol_workbench.core.models import new_id
        items = [
            ("TCP Client", "tcp_client"),
            ("TCP Server", "tcp_server"),
            ("HTTP Client", "http_client"),
            ("HTTP Server", "http_server"),
            ("UDP Endpoint", "udp_endpoint"),
            ("WebSocket Client", "websocket_client"),
            ("WebSocket Server", "websocket_server"),
        ]
        labels = [f"{icon} {name}" for icon, name in [
            ("🔌", "TCP Client"), ("🖥", "TCP Server"),
            ("🌐", "HTTP Client"), ("🖥", "HTTP Server"),
            ("📡", "UDP Endpoint"),
            ("🔌", "WebSocket Client"), ("🖥", "WebSocket Server"),
        ]]
        item, ok = QInputDialog.getItem(
            self, "添加端点", "选择端点类型:", labels, 0, False
        )
        if ok:
            idx = labels.index(item)
            ep_type = items[idx][1]
            ep = EndpointConfig(
                id=new_id(),
                name=f"新{items[idx][0]}",
                type=EndpointType(ep_type),
            )
            self.project_manager.current_project.endpoints.append(ep)
            self.project_changed.emit()
            self.logger.info(f"添加端点: {ep.name}")

    def _add_template(self):
        name, ok = QInputDialog.getText(self, "新建模板", "模板名称:", text="新模板")
        if ok and name:
            from protocol_workbench.core.models import new_id
            tpl = MessageTemplate(id=new_id(), name=name)
            self.project_manager.current_project.message_templates.append(tpl)
            self.project_changed.emit()
            self.logger.info(f"新建模板: {name}")

    def _add_scenario(self):
        from protocol_workbench.core.models import new_id, Scenario
        name, ok = QInputDialog.getText(self, "新建场景", "场景名称:", text="新场景")
        if ok and name:
            sc = Scenario(id=new_id(), name=name)
            self.project_manager.current_project.scenarios.append(sc)
            self.project_changed.emit()
            self.logger.info(f"新建场景: {name}")

    def _rename_endpoint(self, ep_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for ep in project.endpoints:
            if ep.id == ep_id:
                name, ok = QInputDialog.getText(self, "重命名端点", "新名称:", text=ep.name)
                if ok and name:
                    ep.name = name
                    self.project_changed.emit()
                break

    def _rename_template(self, tpl_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for tpl in project.message_templates:
            if tpl.id == tpl_id:
                name, ok = QInputDialog.getText(self, "重命名模板", "新名称:", text=tpl.name)
                if ok and name:
                    tpl.name = name
                    self.project_changed.emit()
                break

    def _rename_scenario(self, sc_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for sc in project.scenarios:
            if sc.id == sc_id:
                name, ok = QInputDialog.getText(self, "重命名场景", "新名称:", text=sc.name)
                if ok and name:
                    sc.name = name
                    self.project_changed.emit()
                break

    def _rename_frame_rule(self, fr_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for fr in project.frame_rules:
            if fr.id == fr_id:
                name, ok = QInputDialog.getText(self, "重命名分帧规则", "新名称:", text=fr.name)
                if ok and name:
                    fr.name = name
                    self.project_changed.emit()
                break

    def _save_project(self):
        if self.project_manager.current_project:
            try:
                self.project_manager.save_project()
                self.logger.info("项目已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _edit_project_info(self):
        project = self.project_manager.current_project
        if not project:
            return
        name, ok = QInputDialog.getText(self, "编辑项目", "项目名称:", text=project.name)
        if ok:
            project.name = name
            self.project_changed.emit()

    def _rename_environment(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for env in project.environments:
            if env.id == env_id:
                name, ok = QInputDialog.getText(self, "重命名环境", "新名称:", text=env.name)
                if ok:
                    env.name = name
                    self.project_changed.emit()
                break

    def _delete_environment(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此环境吗？")
        if reply == QMessageBox.Yes:
            project.environments = [e for e in project.environments if e.id != env_id]
            self.project_changed.emit()

    def _delete_endpoint(self, ep_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此端点吗？")
        if reply == QMessageBox.Yes:
            project.endpoints = [e for e in project.endpoints if e.id != ep_id]
            for env in project.environments:
                env.endpoint_ids = [eid for eid in env.endpoint_ids if eid != ep_id]
            self.project_changed.emit()

    def _delete_template(self, tpl_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此模板吗？")
        if reply == QMessageBox.Yes:
            project.message_templates = [t for t in project.message_templates if t.id != tpl_id]
            self.project_changed.emit()

    def _delete_scenario(self, sc_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此场景吗？")
        if reply == QMessageBox.Yes:
            project.scenarios = [s for s in project.scenarios if s.id != sc_id]
            self.project_changed.emit()

    def _delete_frame_rule(self, fr_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        project.frame_rules = [f for f in project.frame_rules if f.id != fr_id]
        self.project_changed.emit()

    def _add_frame_rule(self):
        from protocol_workbench.core.models import new_id
        project = self.project_manager.current_project
        if not project:
            return
        dialog = FrameRuleDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.get_frame_rule()
            rule.id = new_id()
            project.frame_rules.append(rule)
            self.project_changed.emit()
            self.logger.info(f"新建分帧规则: {rule.name}")

    def _edit_frame_rule(self, fr_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for fr in project.frame_rules:
            if fr.id == fr_id:
                dialog = FrameRuleDialog(fr, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    updated = dialog.get_frame_rule()
                    updated.id = fr.id
                    idx = project.frame_rules.index(fr)
                    project.frame_rules[idx] = updated
                    self.project_changed.emit()
                    self.logger.info(f"分帧规则已更新: {updated.name}")
                break

    def _add_endpoint_to_environment(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        env = None
        for e in project.environments:
            if e.id == env_id:
                env = e
                break
        if not env:
            return

        available = [ep for ep in project.endpoints if ep.id not in env.endpoint_ids]
        if not available:
            QMessageBox.information(self, "提示", "所有端点已在此环境中")
            return

        items = [f"{self._endpoint_icon(ep.type)} {ep.name}" for ep in available]
        item, ok = QInputDialog.getItem(self, "添加端点到环境", "选择端点:", items, 0, False)
        if ok:
            idx = items.index(item)
            ep = available[idx]
            env.endpoint_ids.append(ep.id)
            self.project_changed.emit()
            self.logger.info(f"端点 {ep.name} 已添加到环境 {env.name}")

    def _add_ep_to_env(self, ep_id: str, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for env in project.environments:
            if env.id == env_id:
                if ep_id not in env.endpoint_ids:
                    env.endpoint_ids.append(ep_id)
                    self.project_changed.emit()
                    ep_name = next((ep.name for ep in project.endpoints if ep.id == ep_id), ep_id)
                    self.logger.info(f"端点 {ep_name} 已添加到环境 {env.name}")
                break

    def _remove_ep_from_env(self, ep_id: str, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for env in project.environments:
            if env.id == env_id:
                if ep_id in env.endpoint_ids:
                    env.endpoint_ids.remove(ep_id)
                    self.project_changed.emit()
                    ep_name = next((ep.name for ep in project.endpoints if ep.id == ep_id), ep_id)
                    self.logger.info(f"端点 {ep_name} 已从环境 {env.name} 移除")
                break

    def _manage_environment_variables(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        env = None
        for e in project.environments:
            if e.id == env_id:
                env = e
                break
        if not env:
            return

        dialog = EnvironmentVariableDialog(env, project, self)
        if dialog.exec() == QDialog.Accepted:
            self.project_changed.emit()
            self.logger.info(f"环境变量已更新: {env.name}")


class EnvironmentVariableDialog(QDialog):
    def __init__(self, env: Environment, project: Project, parent=None):
        super().__init__(parent)
        self.env = env
        self.project = project
        self.setWindowTitle(f"环境变量 - {env.name}")
        self.setMinimumSize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_endpoint_tab(), "📡 端点管理")
        tabs.addTab(self._create_variable_tab(), "🔧 变量管理")
        layout.addWidget(tabs)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _create_endpoint_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("环境中的端点:"))
        self.ep_table = QTableWidget()
        self.ep_table.setColumnCount(4)
        self.ep_table.setHorizontalHeaderLabels(["端点名称", "类型", "状态", "操作"])
        header = self.ep_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 120)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 80)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 80)
        self.ep_table.setAlternatingRowColors(True)
        layout.addWidget(self.ep_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加端点")
        add_btn.clicked.connect(self._add_endpoint)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._refresh_endpoints()
        return widget

    def _create_variable_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("环境变量 (覆盖项目变量):"))
        self.var_table = QTableWidget()
        self.var_table.setColumnCount(3)
        self.var_table.setHorizontalHeaderLabels(["变量名", "变量值", "操作"])
        header = self.var_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 80)
        self.var_table.setAlternatingRowColors(True)
        layout.addWidget(self.var_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加变量")
        add_btn.clicked.connect(self._add_variable)
        btn_layout.addWidget(add_btn)

        import_btn = QPushButton("📥 从项目变量导入")
        import_btn.clicked.connect(self._import_project_vars)
        btn_layout.addWidget(import_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._refresh_variables()
        return widget

    def _refresh_endpoints(self):
        self.ep_table.setRowCount(0)
        for ep_id in self.env.endpoint_ids:
            ep = next((e for e in self.project.endpoints if e.id == ep_id), None)
            if not ep:
                continue
            row = self.ep_table.rowCount()
            self.ep_table.insertRow(row)
            self.ep_table.setItem(row, 0, QTableWidgetItem(ep.name))
            self.ep_table.setItem(row, 1, QTableWidgetItem(ep.type.value))
            self.ep_table.setItem(row, 2, QTableWidgetItem("已添加"))
            remove_btn = QPushButton("移除")
            remove_btn.clicked.connect(lambda checked, rid=ep_id: self._remove_endpoint(rid))
            self.ep_table.setCellWidget(row, 3, remove_btn)

    def _refresh_variables(self):
        self.var_table.setRowCount(0)
        for key, value in self.env.variables.items():
            row = self.var_table.rowCount()
            self.var_table.insertRow(row)
            self.var_table.setItem(row, 0, QTableWidgetItem(key))
            self.var_table.setItem(row, 1, QTableWidgetItem(value))
            remove_btn = QPushButton("删除")
            remove_btn.clicked.connect(lambda checked, k=key: self._remove_variable(k))
            self.var_table.setCellWidget(row, 2, remove_btn)

    def _add_endpoint(self):
        available = [ep for ep in self.project.endpoints if ep.id not in self.env.endpoint_ids]
        if not available:
            QMessageBox.information(self, "提示", "所有端点已在此环境中")
            return
        items = [f"{ep.name} ({ep.type.value})" for ep in available]
        item, ok = QInputDialog.getItem(self, "添加端点", "选择端点:", items, 0, False)
        if ok:
            idx = items.index(item)
            self.env.endpoint_ids.append(available[idx].id)
            self._refresh_endpoints()

    def _remove_endpoint(self, ep_id: str):
        if ep_id in self.env.endpoint_ids:
            self.env.endpoint_ids.remove(ep_id)
            self._refresh_endpoints()

    def _add_variable(self):
        key, ok = QInputDialog.getText(self, "添加变量", "变量名:")
        if ok and key:
            value, ok2 = QInputDialog.getText(self, "添加变量", "变量值:")
            if ok2:
                self.env.variables[key] = value
                self._refresh_variables()

    def _remove_variable(self, key: str):
        if key in self.env.variables:
            del self.env.variables[key]
            self._refresh_variables()

    def _import_project_vars(self):
        for key, value in self.project.variables.items():
            if key not in self.env.variables:
                self.env.variables[key] = value
        self._refresh_variables()


class FrameRuleDialog(QDialog):
    def __init__(self, rule: FrameRule | None = None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("编辑分帧规则" if rule else "新建分帧规则")
        self.setMinimumWidth(500)
        self._setup_ui()
        if rule:
            self._load_rule(rule)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("规则名称:", self.name_edit)

        self.mode_combo = QComboBox()
        for m in FrameMode:
            labels = {"raw": "Raw (原始)", "delimiter": "分隔符", "start_end": "起止标志", "length_prefix": "长度前缀"}
            self.mode_combo.addItem(labels.get(m.value, m.value), m.value)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("分帧模式:", self.mode_combo)

        self.delimiter_edit = QLineEdit("\n")
        self.delimiter_edit.setPlaceholderText("如: \\n 或 \\r\\n 或 |")
        form.addRow("分隔符:", self.delimiter_edit)

        self.start_flag_edit = QLineEdit()
        self.start_flag_edit.setPlaceholderText("如: * 或 0xAA")
        form.addRow("起始标志:", self.start_flag_edit)

        self.end_flag_edit = QLineEdit()
        self.end_flag_edit.setPlaceholderText("如: # 或 0x55")
        form.addRow("结束标志:", self.end_flag_edit)

        self.length_offset_spin = QSpinBox()
        self.length_offset_spin.setRange(0, 1024)
        form.addRow("长度字段偏移:", self.length_offset_spin)

        self.length_size_spin = QSpinBox()
        self.length_size_spin.setRange(1, 8)
        self.length_size_spin.setValue(4)
        form.addRow("长度字段大小(字节):", self.length_size_spin)

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItem("大端 (Big Endian)", "big")
        self.byte_order_combo.addItem("小端 (Little Endian)", "little")
        form.addRow("字节序:", self.byte_order_combo)

        self.length_includes_check = QCheckBox("长度值包含头部")
        form.addRow("", self.length_includes_check)

        self.fixed_length_spin = QSpinBox()
        self.fixed_length_spin.setRange(1, 65536)
        form.addRow("固定长度:", self.fixed_length_spin)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._on_mode_changed(0)

    def _on_mode_changed(self, index: int):
        mode = self.mode_combo.currentData()
        is_delimiter = mode == "delimiter"
        is_start_end = mode == "start_end"
        is_length = mode == "length_prefix"
        is_raw = mode == "raw"

        self.delimiter_edit.setVisible(is_delimiter)
        self.start_flag_edit.setVisible(is_start_end)
        self.end_flag_edit.setVisible(is_start_end)
        self.length_offset_spin.setVisible(is_length)
        self.length_size_spin.setVisible(is_length)
        self.byte_order_combo.setVisible(is_length)
        self.length_includes_check.setVisible(is_length)
        self.fixed_length_spin.setVisible(is_raw)

        parent_form = self.delimiter_edit.parent()
        if parent_form:
            for i in range(parent_form.layout().rowCount()):
                label_item = parent_form.layout().itemAt(i, QFormLayout.LabelRole)
                field_item = parent_form.layout().itemAt(i, QFormLayout.FieldRole)
                if field_item and field_item.widget():
                    widget = field_item.widget()
                    if widget == self.delimiter_edit:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_delimiter)
                    elif widget == self.start_flag_edit:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_start_end)
                    elif widget == self.end_flag_edit:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_start_end)
                    elif widget == self.length_offset_spin:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_length)
                    elif widget == self.length_size_spin:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_length)
                    elif widget == self.byte_order_combo:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_length)
                    elif widget == self.length_includes_check:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_length)
                    elif widget == self.fixed_length_spin:
                        if label_item and label_item.widget():
                            label_item.widget().setVisible(is_raw)

    def _load_rule(self, rule: FrameRule):
        self.name_edit.setText(rule.name)
        idx = self.mode_combo.findData(rule.mode.value)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.delimiter_edit.setText(rule.delimiter)
        self.start_flag_edit.setText(rule.start_flag)
        self.end_flag_edit.setText(rule.end_flag)
        self.length_offset_spin.setValue(rule.length_field_offset)
        self.length_size_spin.setValue(rule.length_field_size)
        idx = self.byte_order_combo.findData(rule.byte_order)
        if idx >= 0:
            self.byte_order_combo.setCurrentIndex(idx)
        self.length_includes_check.setChecked(rule.length_includes_header)
        self.fixed_length_spin.setValue(rule.fixed_length)
        self._on_mode_changed(self.mode_combo.currentIndex())

    def get_frame_rule(self) -> FrameRule:
        return FrameRule(
            name=self.name_edit.text(),
            mode=FrameMode(self.mode_combo.currentData()),
            delimiter=self.delimiter_edit.text(),
            start_flag=self.start_flag_edit.text(),
            end_flag=self.end_flag_edit.text(),
            length_field_offset=self.length_offset_spin.value(),
            length_field_size=self.length_size_spin.value(),
            byte_order=self.byte_order_combo.currentData(),
            length_includes_header=self.length_includes_check.isChecked(),
            fixed_length=self.fixed_length_spin.value(),
        )
