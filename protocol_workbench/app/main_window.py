from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QStatusBar,
    QFileDialog, QMessageBox, QApplication, QToolBar,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QComboBox, QSpinBox, QPushButton,
)

from protocol_workbench import __version__

from protocol_workbench.app.theme import DARK_THEME_QSS
from protocol_workbench.app.project_panel import ProjectPanel
from protocol_workbench.app.endpoint_panel import EndpointPanel
from protocol_workbench.app.message_editor_panel import MessageEditorPanel
from protocol_workbench.app.template_panel import TemplatePanel
from protocol_workbench.app.scenario_panel import ScenarioPanel
from protocol_workbench.app.log_panel import LogPanel
from protocol_workbench.app.console_panel import ConsolePanel
from protocol_workbench.core.config_store import ConfigStore
from protocol_workbench.core.project_manager import ProjectManager
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.core.runtime_manager import RuntimeManager
from protocol_workbench.core.variable_engine import VariableEngine
from protocol_workbench.core.template_engine import TemplateEngine
from protocol_workbench.scenario.scenario_runner import ScenarioRunner
from protocol_workbench.core.models import Project, EndpointConfig, Environment, MessageTemplate, FrameRule, TemplateCategory, PayloadType


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Protocol Workbench - 协议联调工作台")
        self.setMinimumSize(1280, 800)
        self.resize(1600, 900)

        self.config_store = ConfigStore()
        self.project_manager = ProjectManager(self.config_store)
        self.logger = LoggerService()
        self.variable_engine = VariableEngine()
        self.template_engine = TemplateEngine(self.variable_engine)
        self.runtime_manager = RuntimeManager(self.logger)
        self.scenario_runner = ScenarioRunner(self.runtime_manager, self.logger)

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()

        last_path = self.config_store.get_last_project_path()
        if last_path:
            try:
                project = self.project_manager.open_project(last_path)
                self._ensure_spi_templates(project)
                self.runtime_manager.set_project(project)
                self.scenario_runner.set_project(project)
                self.variable_engine.set_project_variables(project.variables)
                self.runtime_manager.variable_engine = self.variable_engine
                self.runtime_manager.template_engine = TemplateEngine(self.variable_engine)
                self._refresh_all_panels()
                self.project_label.setText(f"项目: {project.name}")
                self.logger.info(f"已加载上次项目: {project.name}")
            except Exception as e:
                self.logger.warn(f"加载上次项目失败: {e}，创建新项目")
                self._new_project()
        else:
            self._new_project()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Horizontal)

        self.project_panel = ProjectPanel(self.project_manager, self.logger, self)
        self.project_panel.setMinimumWidth(240)
        self.project_panel.setMaximumWidth(400)

        right_splitter = QSplitter(Qt.Vertical)

        self.work_tabs = QTabWidget()
        self.work_tabs.setDocumentMode(True)
        self.work_tabs.setMovable(True)
        self.work_tabs.setTabsClosable(False)

        self.endpoint_panel = EndpointPanel(
            self.runtime_manager, self.project_manager, self.logger, self
        )
        self.message_editor = MessageEditorPanel(
            self.template_engine, self.variable_engine, self.logger,
            self.project_manager, self
        )
        self.template_panel = TemplatePanel(
            self.project_manager, self.template_engine, self.logger, self
        )
        self.scenario_panel = ScenarioPanel(
            self.scenario_runner, self.project_manager, self.logger, self
        )

        self.work_tabs.addTab(self.endpoint_panel, "📡 端点管理")
        self.work_tabs.addTab(self.message_editor, "📝 消息编辑器")
        self.work_tabs.addTab(self.template_panel, "📋 模板管理")
        self.work_tabs.addTab(self.scenario_panel, "🎬 场景编排")

        bottom_splitter = QSplitter(Qt.Horizontal)
        self.log_panel = LogPanel(self.logger, self)
        self.console_panel = ConsolePanel(self.logger, self)
        bottom_splitter.addWidget(self.log_panel)
        bottom_splitter.addWidget(self.console_panel)
        bottom_splitter.setSizes([700, 300])
        self.console_panel.hide()

        right_splitter.addWidget(self.work_tabs)
        right_splitter.addWidget(bottom_splitter)
        right_splitter.setSizes([600, 200])
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        self.main_splitter.addWidget(self.project_panel)
        self.main_splitter.addWidget(right_splitter)
        self.main_splitter.setSizes([280, 1320])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.main_splitter)

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        new_action = QAction("新建项目(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("打开项目(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        save_action = QAction("保存项目(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("导出项目包(&E)", self)
        export_action.triggered.connect(self._export_project)
        file_menu.addAction(export_action)

        import_action = QAction("导入项目包(&I)", self)
        import_action.triggered.connect(self._import_project)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        env_menu = menubar.addMenu("环境(&E)")
        add_env_action = QAction("新建环境", self)
        add_env_action.triggered.connect(self._add_environment)
        env_menu.addAction(add_env_action)

        endpoint_menu = menubar.addMenu("端点(&P)")
        add_tcp_client = QAction("添加 TCP Client", self)
        add_tcp_client.triggered.connect(lambda: self._add_endpoint("tcp_client"))
        endpoint_menu.addAction(add_tcp_client)

        add_tcp_server = QAction("添加 TCP Server", self)
        add_tcp_server.triggered.connect(lambda: self._add_endpoint("tcp_server"))
        endpoint_menu.addAction(add_tcp_server)

        add_http_client = QAction("添加 HTTP Client", self)
        add_http_client.triggered.connect(lambda: self._add_endpoint("http_client"))
        endpoint_menu.addAction(add_http_client)

        add_http_server = QAction("添加 HTTP Server", self)
        add_http_server.triggered.connect(lambda: self._add_endpoint("http_server"))
        endpoint_menu.addAction(add_http_server)

        add_udp = QAction("添加 UDP Endpoint", self)
        add_udp.triggered.connect(lambda: self._add_endpoint("udp_endpoint"))
        endpoint_menu.addAction(add_udp)

        add_ws_client = QAction("添加 WebSocket Client", self)
        add_ws_client.triggered.connect(lambda: self._add_endpoint("websocket_client"))
        endpoint_menu.addAction(add_ws_client)

        add_ws_server = QAction("添加 WebSocket Server", self)
        add_ws_server.triggered.connect(lambda: self._add_endpoint("websocket_server"))
        endpoint_menu.addAction(add_ws_server)

        help_menu = menubar.addMenu("帮助(&H)")
        manual_action = QAction("用户手册(&M)", self)
        manual_action.setShortcut("F1")
        manual_action.triggered.connect(self._show_manual)
        help_menu.addAction(manual_action)
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        new_btn = toolbar.addAction("📄 新建")
        new_btn.triggered.connect(self._new_project)
        open_btn = toolbar.addAction("📂 打开")
        open_btn.triggered.connect(self._open_project)
        save_btn = toolbar.addAction("💾 保存")
        save_btn.triggered.connect(self._save_project)

        toolbar.addSeparator()

        start_all_btn = toolbar.addAction("▶ 启动全部")
        start_all_btn.triggered.connect(self._start_all_endpoints)
        stop_all_btn = toolbar.addAction("⏹ 停止全部")
        stop_all_btn.triggered.connect(self._stop_all_endpoints)

        toolbar.addSeparator()

        export_btn = toolbar.addAction("📤 导出")
        export_btn.triggered.connect(self._export_project)

        self._init_continuous_report_toolbar(toolbar)

    def _init_continuous_report_toolbar(self, toolbar: QToolBar):
        """在工具栏中添加持续上报控制区域"""
        toolbar.addSeparator()

        self.cont_report_label = QLabel(" 持续上报:")
        toolbar.addWidget(self.cont_report_label)

        self.cont_report_combo = QComboBox()
        self.cont_report_combo.setMinimumWidth(180)
        self.cont_report_combo.setToolTip("选择要持续上报的模板")
        toolbar.addWidget(self.cont_report_combo)

        self.cont_report_interval = QSpinBox()
        self.cont_report_interval.setRange(1, 3600)
        self.cont_report_interval.setValue(5)
        self.cont_report_interval.setSuffix(" 秒")
        self.cont_report_interval.setToolTip("上报间隔（秒）")
        self.cont_report_interval.setMaximumWidth(90)
        toolbar.addWidget(self.cont_report_interval)

        self.cont_report_btn = QPushButton("▶ 开始上报")
        self.cont_report_btn.setProperty("class", "primary")
        self.cont_report_btn.setMaximumWidth(110)
        self.cont_report_btn.setCheckable(True)
        self.cont_report_btn.toggled.connect(self._on_continuous_report_toggled)
        toolbar.addWidget(self.cont_report_btn)

        self.cont_report_count_label = QLabel(" 0")
        toolbar.addWidget(self.cont_report_count_label)

        self._cont_report_timer = QTimer(self)
        self._cont_report_timer.timeout.connect(self._do_continuous_report)
        self._cont_report_count = 0

        self._active_env_id = ""
        self._active_env_name = ""
        self._active_env_mode = "backend"
        self._active_env_endpoint_ids = []

    def _init_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label, 1)
        self.project_label = QLabel("项目: 未创建")
        self.statusbar.addPermanentWidget(self.project_label)

    def _connect_signals(self):
        self.project_panel.project_changed.connect(self._on_project_changed)
        self.project_panel.endpoint_selected.connect(self._on_endpoint_selected)
        self.project_panel.template_selected.connect(self._on_template_selected)
        self.project_panel.scenario_selected.connect(self._on_scenario_selected)
        self.project_panel.environment_start_requested.connect(self._on_environment_start)
        self.project_panel.environment_stop_requested.connect(self._on_environment_stop)
        self.project_panel.environment_selected.connect(self._on_environment_selected)

        self.runtime_manager.endpoint_state_changed.connect(self._on_endpoint_state_changed)
        self.runtime_manager.data_received.connect(self._on_data_received)
        self.runtime_manager.data_sent.connect(self._on_data_sent)

        self.endpoint_panel.send_requested.connect(self._on_send_requested)
        self.template_panel.edit_template_requested.connect(self._on_edit_template)
        self.message_editor.quick_send_requested.connect(self._on_quick_send)

    def _new_project(self):
        project = self.project_manager.new_project("新项目")
        self._load_default_spi_templates(project)
        self.runtime_manager.set_project(project)
        self.scenario_runner.set_project(project)
        self.variable_engine.set_project_variables(project.variables)
        self.runtime_manager.variable_engine = self.variable_engine
        self.runtime_manager.template_engine = TemplateEngine(self.variable_engine)
        self._refresh_all_panels()
        self.project_label.setText(f"项目: {project.name}")
        self.logger.info(f"新建项目: {project.name}")

    def _ensure_spi_templates(self, project: Project):
        self._load_default_spi_templates(project, skip_existing=True)
        self._migrate_template_endpoint_binding(project)

    def _migrate_template_endpoint_binding(self, project: Project):
        orphan_tpls = [t for t in project.message_templates if not t.endpoint_id]
        if not orphan_tpls:
            return
        server_eps = [ep for ep in project.endpoints if ep.type.value in ("tcp_server", "http_server", "websocket_server")]
        client_eps = [ep for ep in project.endpoints if ep.type.value in ("tcp_client", "http_client", "websocket_client")]
        report_cats = {"report_device_status", "report_alarm", "report_img", "report_high_range", "report_range_result", "report_task", "heartbeat", "response", "ack"}
        if server_eps:
            for tpl in orphan_tpls:
                if tpl.category.value in report_cats:
                    tpl.endpoint_id = server_eps[0].id
                elif client_eps:
                    tpl.endpoint_id = client_eps[0].id
                elif project.endpoints:
                    tpl.endpoint_id = project.endpoints[0].id
        elif len(project.endpoints) >= 2:
            up_ep = None
            back_ep = None
            for ep in project.endpoints:
                name_lower = ep.name.lower()
                if "server" in name_lower:
                    up_ep = ep
                elif "client" in name_lower:
                    back_ep = ep
            if not up_ep:
                for ep in project.endpoints:
                    if "上位" in ep.name:
                        up_ep = ep
                        break
            if not back_ep:
                for ep in project.endpoints:
                    if "后端" in ep.name or "测试" in ep.name:
                        back_ep = ep
                        break
            if not up_ep:
                up_ep = project.endpoints[0]
            if not back_ep:
                back_ep = project.endpoints[-1]
            for tpl in orphan_tpls:
                if tpl.category.value in report_cats:
                    tpl.endpoint_id = up_ep.id
                else:
                    tpl.endpoint_id = back_ep.id
        elif project.endpoints:
            for tpl in orphan_tpls:
                tpl.endpoint_id = project.endpoints[0].id
        for env in project.environments:
            if not env.endpoint_ids:
                env.endpoint_ids = [ep.id for ep in project.endpoints]
        migrated = sum(1 for t in orphan_tpls if t.endpoint_id)
        if migrated:
            self.logger.info(f"已迁移 {migrated} 个模板绑定到端点")

    def _load_default_spi_templates(self, project: Project, skip_existing: bool = False):
        import json as _json
        try:
            if skip_existing and project.message_templates:
                return
            try:
                base = Path(sys._MEIPASS)
            except AttributeError:
                base = Path(__file__).parent.parent
            tmpl_path = base / "protocol_workbench" / "resources" / "default_templates.json"
            if not tmpl_path.exists():
                self.logger.warn("默认模板文件不存在，跳过加载")
                return
            with open(tmpl_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            templates = data.get("templates", [])
            first_ep_id = project.endpoints[0].id if project.endpoints else ""
            added = 0
            for section in templates:
                for entry in section.get("entries", []):
                    tpl = MessageTemplate(
                        name=entry.get("name", ""),
                        endpoint_id=first_ep_id,
                        category=TemplateCategory(entry.get("category", "message")),
                        payload_type=PayloadType(entry.get("payload_type", "json")),
                    )
                    msg_type = entry.get("msgType", "")
                    is_report = (msg_type == "report")
                    msg_id = entry.get("_response_header_msgId", "${uuid_short}")
                    header = {
                        "msgId": msg_id,
                        "msgType": msg_type,
                        "timestamp": "${now_ms}",
                        "from": "client" if is_report else "server",
                        "to": "server" if is_report else "client",
                    }
                    body = {}
                    theme = entry.get("theme", "")
                    content = entry.get("content", {})
                    if content:
                        body["theme"] = theme
                        body["content"] = content
                    resp_body = entry.get("_response_body")
                    if resp_body:
                        body = resp_body
                    tpl.content = _json.dumps({"header": header, "body": body}, ensure_ascii=False, indent=2)
                    project.message_templates.append(tpl)
                    added += 1
            self.logger.info(f"已加载 {added} 个 SPI 默认协议模板")
        except Exception as e:
            self.logger.warn(f"加载默认模板失败: {e}")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                project = self.project_manager.open_project(path)
                self._ensure_spi_templates(project)
                self.config_store.set_last_project_path(path)
                self.runtime_manager.set_project(project)
                self.scenario_runner.set_project(project)
                self.variable_engine.set_project_variables(project.variables)
                self.runtime_manager.variable_engine = self.variable_engine
                self.runtime_manager.template_engine = TemplateEngine(self.variable_engine)
                self._refresh_all_panels()
                self.project_label.setText(f"项目: {project.name}")
                self.logger.info(f"打开项目: {project.name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开项目失败: {e}")

    def _save_project(self):
        if self.project_manager.current_project:
            try:
                path = self.project_manager.save_project()
                self.config_store.set_last_project_path(path)
                self.logger.info("项目已保存")
                self.status_label.setText("项目已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存项目失败: {e}")

    def _export_project(self):
        if not self.project_manager.current_project:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出项目", f"{self.project_manager.current_project.name}",
            "JSON 文件 (*.json);;ZIP 项目包 (*.zip)"
        )
        if path:
            try:
                if path.endswith(".zip"):
                    self.project_manager.export_project(export_path=path)
                else:
                    if not path.endswith(".json"):
                        path += ".json"
                    self.config_store.save_project(self.project_manager.current_project, path)
                self.logger.info(f"项目已导出: {path}")
                self.status_label.setText(f"项目已导出: {path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _import_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入项目", "", "项目文件 (*.json *.zip);;JSON 文件 (*.json);;ZIP 文件 (*.zip);;所有文件 (*)"
        )
        if path:
            try:
                if path.endswith(".zip"):
                    project = self.project_manager.import_project(path)
                else:
                    project = self.project_manager.open_project(path)
                self.config_store.set_last_project_path(path)
                self.runtime_manager.set_project(project)
                self.scenario_runner.set_project(project)
                self.variable_engine.set_project_variables(project.variables)
                self.runtime_manager.variable_engine = self.variable_engine
                self.runtime_manager.template_engine = TemplateEngine(self.variable_engine)
                self._refresh_all_panels()
                self.logger.info(f"项目已导入: {project.name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def _add_environment(self):
        if self.project_manager.current_project:
            from protocol_workbench.core.models import new_id
            env = Environment(id=new_id(), name="新环境")
            self.project_manager.current_project.environments.append(env)
            self._refresh_all_panels()
            self.logger.info(f"添加环境: {env.name}")

    def _add_endpoint(self, endpoint_type: str):
        if self.project_manager.current_project:
            from protocol_workbench.core.models import EndpointConfig, EndpointType, new_id, FrameRule, FrameMode
            ep = EndpointConfig(
                id=new_id(),
                name=f"新端点_{endpoint_type}",
                type=EndpointType(endpoint_type),
            )
            if "tcp" in endpoint_type and not self.project_manager.current_project.frame_rules:
                self.project_manager.current_project.frame_rules.append(
                    FrameRule(id=new_id(), name="SPI-*JSON#", mode=FrameMode.START_END,
                              start_flag="*", end_flag="#"))
            self.project_manager.current_project.endpoints.append(ep)
            self._refresh_all_panels()
            self.logger.info(f"添加端点: {ep.name}")

    def _start_all_endpoints(self):
        if self.project_manager.current_project:
            for ep in self.project_manager.current_project.endpoints:
                asyncio.create_task(self.runtime_manager.start_endpoint(ep))

    def _stop_all_endpoints(self):
        asyncio.create_task(self.runtime_manager.stop_all())

    def _show_manual(self):
        from PySide6.QtWidgets import QDialog, QTextBrowser, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("用户手册 - Protocol Workbench")
        dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(dialog)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._get_manual_html())
        layout.addWidget(browser)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        dialog.exec()

    @staticmethod
    def _get_manual_html() -> str:
        return """
        <html><head><style>
        body { font-family: "Microsoft YaHei", sans-serif; color: #cdd6f4; background: #1e1e2e; padding: 20px; }
        h1 { color: #89b4fa; border-bottom: 2px solid #89b4fa; padding-bottom: 8px; }
        h2 { color: #f9e2af; margin-top: 24px; }
        h3 { color: #a6e3a1; }
        p, li { line-height: 1.8; }
        code { background: #313244; padding: 2px 6px; border-radius: 3px; color: #f38ba8; }
        .section { margin-bottom: 20px; }
        .tip { background: #1e1e2e; border-left: 4px solid #f9e2af; padding: 8px 12px; margin: 8px 0; }
        </style></head><body>
        <h1>📖 Protocol Workbench 用户手册</h1>

        <div class="section">
        <h2>1. 快速开始</h2>
        <h3>1.1 新建项目</h3>
        <p>点击菜单 <code>文件 → 新建项目</code> 或工具栏 <code>📄 新建</code> 按钮，输入项目名称即可创建。</p>
        <h3>1.2 添加端点</h3>
        <p>在左侧项目面板中，右键点击 <b>端点</b> 节点，选择 <b>新建端点</b>；或通过菜单 <code>端点</code> 添加指定类型的端点。</p>
        <p>支持的端点类型：</p>
        <ul>
          <li><b>TCP Client</b> - 主动连接TCP服务器</li>
          <li><b>TCP Server</b> - 监听TCP端口等待连接</li>
          <li><b>HTTP Client</b> - 发送HTTP请求 (GET/POST/PUT/DELETE)</li>
          <li><b>HTTP Server</b> - 监听HTTP端口，支持自动回复</li>
          <li><b>UDP Endpoint</b> - UDP收发</li>
          <li><b>WebSocket Client</b> - 连接WebSocket服务器</li>
          <li><b>WebSocket Server</b> - 监听WebSocket端口</li>
        </ul>
        <h3>1.3 编辑消息</h3>
        <p>切换到 <b>📝 消息编辑器</b> 标签页，选择端点后可以：</p>
        <ul>
          <li>在 <b>源码视图</b> 中直接编辑JSON文本</li>
          <li>在 <b>树形视图</b> 中以可视化方式添加/编辑/删除字段</li>
          <li>使用 <code>${变量名}</code> 语法插入环境变量</li>
        </ul>
        <h3>1.4 发送与接收</h3>
        <p>在端点面板中，选中一个已启动的端点，输入消息内容后点击 <b>发送</b> 按钮即可发送。接收到的数据会在下方的接收区域显示，并以端点名称和方向(TX/RX)区分。</p>
        </div>

        <div class="section">
        <h2>2. 核心功能</h2>
        <h3>2.1 模板管理</h3>
        <p>在 <b>📋 模板管理</b> 标签页中，可以创建、编辑、复制和删除消息模板。模板支持：</p>
        <ul>
          <li>分类管理（请求/响应/通知/心跳）</li>
          <li>Payload类型（JSON/Text/Hex）</li>
          <li>发送模式（仅发送/仅接收/发送等待响应/接收后回复/心跳）</li>
          <li>变量替换 <code>${变量名}</code></li>
        </ul>
        <div class="tip">💡 模板可以导出为JSON文件，分享给同事使用。</div>

        <h3>2.2 场景编排</h3>
        <p>在 <b>🎬 场景编排</b> 标签页中，可以创建测试场景：</p>
        <ul>
          <li>添加多个步骤，每个步骤指定端点和模板</li>
          <li>设置步骤间延迟时间</li>
          <li>支持串行和并行执行模式</li>
          <li>支持循环和数据驱动（CSV/JSON数据源）</li>
        </ul>

        <h3>2.3 环境管理</h3>
        <p>右键左侧项目面板的 <b>环境</b> 节点，可以：</p>
        <ul>
          <li>创建多个环境（如开发/测试/生产）</li>
          <li>每个环境可配置不同的端点和变量</li>
          <li>切换环境后变量自动替换</li>
        </ul>

        <h3>2.4 分帧规则</h3>
        <p>支持自定义TCP分帧规则：</p>
        <ul>
          <li><b>Raw</b> - 原始数据，不分帧</li>
          <li><b>Delimiter</b> - 按分隔符分帧（如 \\n）</li>
          <li><b>Start-End</b> - 按起始/结束标记分帧</li>
          <li><b>Length-Prefix</b> - 按长度前缀分帧</li>
        </ul>
        </div>

        <div class="section">
        <h2>3. 项目管理</h2>
        <h3>3.1 保存与加载</h3>
        <p>项目配置以JSON格式保存。点击 <code>文件 → 保存项目</code> 或 <code>Ctrl+S</code> 保存。</p>
        <div class="tip">💡 保存的项目文件可以直接发送给同事，对方通过 <code>文件 → 打开项目</code> 即可加载使用。</div>

        <h3>3.2 导出与导入</h3>
        <p><code>文件 → 导出项目包</code> 将项目导出为独立的JSON文件，<code>文件 → 导入项目包</code> 从JSON文件加载项目。</p>

        <h3>3.3 自动加载</h3>
        <p>上次打开的项目会在下次启动时自动加载。</p>
        </div>

        <div class="section">
        <h2>4. 日志与调试</h2>
        <h3>4.1 运行日志</h3>
        <p>底部 <b>日志</b> 面板显示所有运行日志，包括：</p>
        <ul>
          <li>协议类型、端点名称、源/目标地址</li>
          <li>发送/接收字节数</li>
          <li>错误和警告信息</li>
        </ul>
        <p>支持按级别过滤（DEBUG/INFO/WARN/ERROR/TX/RX）。</p>

        <h3>4.2 报文记录</h3>
        <p>切换到 <b>报文记录</b> 标签页，可以查看所有收发报文的详细信息：</p>
        <ul>
          <li>双击行查看完整报文详情（解析视图/Hex视图/JSON视图）</li>
          <li>选中两行报文后可进行对比</li>
          <li>支持报文回放</li>
        </ul>

        <h3>4.3 命令控制台</h3>
        <p>底部 <b>控制台</b> 面板支持命令行操作：</p>
        <ul>
          <li><code>help</code> - 查看所有命令</li>
          <li><code>list endpoints</code> - 列出端点及状态</li>
          <li><code>status</code> - 查看项目状态</li>
          <li><code>clear</code> - 清空控制台</li>
        </ul>
        </div>

        <div class="section">
        <h2>5. 快捷键</h2>
        <table style="width:100%; border-collapse:collapse;">
          <tr style="background:#313244;"><th style="padding:6px;text-align:left;">快捷键</th><th style="padding:6px;text-align:left;">功能</th></tr>
          <tr><td style="padding:4px;"><code>Ctrl+N</code></td><td>新建项目</td></tr>
          <tr><td style="padding:4px;"><code>Ctrl+O</code></td><td>打开项目</td></tr>
          <tr><td style="padding:4px;"><code>Ctrl+S</code></td><td>保存项目</td></tr>
          <tr><td style="padding:4px;"><code>Ctrl+Q</code></td><td>退出</td></tr>
          <tr><td style="padding:4px;"><code>F1</code></td><td>用户手册</td></tr>
        </table>
        </div>

        <div class="section">
        <h2>6. 常见问题</h2>
        <h3>Q: 端点启动失败？</h3>
        <p>A: 检查端口是否被占用，可在端点配置中更换端口。</p>
        <h3>Q: 发送消息后没有响应？</h3>
        <p>A: 确认端点已成功启动，检查目标地址和端口是否正确，查看日志面板的错误信息。</p>
        <h3>Q: 如何与同事共享配置？</h3>
        <p>A: 使用 <code>文件 → 导出项目包</code> 导出JSON文件，发送给同事后通过 <code>文件 → 导入项目包</code> 加载。</p>
        </div>
        </body></html>
        """

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            f"协议联调工作台 v{__version__}\n\n"
            "用于后端、上位机设备端、前端接口之间的\n"
            "协议测试、接口验证、场景仿真和问题复现。\n\n"
            "支持 TCP / HTTP / UDP / WebSocket"
        )

    def _on_project_changed(self):
        project = self.project_manager.current_project
        if project:
            self.runtime_manager.set_project(project)
            self.scenario_runner.set_project(project)
            self.variable_engine.set_project_variables(project.variables)
            self.runtime_manager.variable_engine = self.variable_engine
            self.runtime_manager.template_engine = TemplateEngine(self.variable_engine)
            self.project_label.setText(f"项目: {project.name}")
        if hasattr(self, '_active_env_id') and self._active_env_id:
            self._on_environment_selected(self._active_env_id)
        else:
            self._refresh_all_panels()

    def _on_endpoint_selected(self, endpoint_id: str):
        self.work_tabs.setCurrentIndex(0)
        self.endpoint_panel.select_endpoint(endpoint_id)
        self.message_editor.set_endpoint_filter(endpoint_id)

    def _on_template_selected(self, template_id: str):
        self.work_tabs.setCurrentIndex(2)
        self.template_panel.select_template(template_id)
        project = self.project_manager.current_project
        if project:
            for tpl in project.message_templates:
                if tpl.id == template_id and tpl.endpoint_id:
                    self.message_editor.set_endpoint_filter(tpl.endpoint_id)
                    break

    def _on_scenario_selected(self, scenario_id: str):
        self.work_tabs.setCurrentIndex(3)
        self.scenario_panel.select_scenario(scenario_id)

    def _on_environment_start(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for env in project.environments:
            if env.id == env_id:
                for ep_id in env.endpoint_ids:
                    for ep in project.endpoints:
                        if ep.id == ep_id:
                            asyncio.create_task(self.runtime_manager.start_endpoint(ep))
                self.logger.info(f"环境已启动: {env.name}")
                break

    def _on_environment_stop(self, env_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for env in project.environments:
            if env.id == env_id:
                for ep_id in env.endpoint_ids:
                    asyncio.create_task(self.runtime_manager.stop_endpoint(ep_id))
                self.logger.info(f"环境已停止: {env.name}")
                break

    def _on_environment_selected(self, env_id: str):
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

        self._active_env_id = env_id
        self._active_env_name = env.name
        is_up_comp = ("上位机" in env.name or "upper" in env.name.lower() or "up" in env.name.lower())
        self._active_env_mode = "upper_computer" if is_up_comp else "backend"

        if not env.endpoint_ids:
            for ep in project.endpoints:
                if is_up_comp and ("server" in ep.name.lower() or ep.type.value in ("tcp_server", "http_server", "websocket_server")):
                    env.endpoint_ids.append(ep.id)
                elif not is_up_comp and ("client" in ep.name.lower() or ep.type.value in ("tcp_client", "http_client", "websocket_client")):
                    env.endpoint_ids.append(ep.id)
            if not env.endpoint_ids:
                env.endpoint_ids = [ep.id for ep in project.endpoints]
        self._active_env_endpoint_ids = list(env.endpoint_ids)

        self.endpoint_panel.set_environment_filter(env.name, env.endpoint_ids, self._active_env_mode)
        self.template_panel.set_endpoint_ids_filter(env.endpoint_ids)

        first_ep_id = env.endpoint_ids[0] if env.endpoint_ids else ""
        self.message_editor.set_endpoint_filter(first_ep_id)

        mode_label = "上位机模拟" if is_up_comp else "后端测试"
        self.status_label.setText(f"当前环境: {env.name} [{mode_label}]")
        self.logger.info(f"切换到环境: {env.name} ({mode_label})")
        self._refresh_all_panels()

    def _on_endpoint_state_changed(self, endpoint_id: str, state: str):
        self.endpoint_panel.update_endpoint_state(endpoint_id, state)
        self.project_panel.update_endpoint_state(endpoint_id, state)

    def _on_data_received(self, endpoint_id: str, data: bytes, remote_addr: str):
        project = self.project_manager.current_project
        ep_name = ""
        ep_payload = "text"
        ep_type = ""
        if project:
            for ep in project.endpoints:
                if ep.id == endpoint_id:
                    ep_name = ep.name
                    ep_payload = ep.payload_type.value
                    ep_type = ep.type.value
                    break
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.hex()

        if ep_payload == "json":
            try:
                import json as _json
                parsed = _json.loads(text)
                text = _json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                pass

        self.endpoint_panel.append_rx_data(f"{text}", ep_name, "RX")

    def _on_data_sent(self, endpoint_id: str, data: bytes, target: str):
        project = self.project_manager.current_project
        ep_name = ""
        if project:
            for ep in project.endpoints:
                if ep.id == endpoint_id:
                    ep_name = ep.name
                    break
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.hex()
        try:
            import json as _json
            parsed = _json.loads(text)
            text = _json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self.endpoint_panel.append_rx_data(f"{text}", ep_name, "TX")

    def _on_send_requested(self, endpoint_id: str, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        template = None
        ep = None
        ep_name = ""
        for t in project.message_templates:
            if t.id == template_id:
                template = t
                break
        for ep in project.endpoints:
            if ep.id == endpoint_id:
                ep_name = ep.name
                break
        else:
            ep = None
        if template:
            rendered = self.runtime_manager.template_engine.render(template)
            display_text = rendered
            if ep and ep.payload_type.value == "json":
                try:
                    import json as _json
                    parsed = _json.loads(rendered)
                    display_text = _json.dumps(parsed, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            self.endpoint_panel.append_rx_data(f"{display_text}", ep_name, "TX")
            asyncio.create_task(self.runtime_manager.send_message(endpoint_id, template))

    def _on_edit_template(self, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        for t in project.message_templates:
            if t.id == template_id:
                if t.endpoint_id:
                    self.message_editor.set_endpoint_filter(t.endpoint_id)
                self.message_editor.load_template(t)
                self.work_tabs.setCurrentIndex(1)
                break

    def _on_quick_send(self, endpoint_id: str, template_id: str):
        project = self.project_manager.current_project
        if not project:
            return
        template = None
        ep = None
        ep_name = ""
        for t in project.message_templates:
            if t.id == template_id:
                template = t
                break
        for ep in project.endpoints:
            if ep.id == endpoint_id:
                ep_name = ep.name
                break
        else:
            ep = None
        if template:
            rendered = self.runtime_manager.template_engine.render(template)
            display_text = rendered
            if ep and ep.payload_type.value == "json":
                try:
                    import json as _json
                    parsed = _json.loads(rendered)
                    display_text = _json.dumps(parsed, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            self.endpoint_panel.append_rx_data(f"{display_text}", ep_name, "TX")
            asyncio.create_task(self.runtime_manager.send_message(endpoint_id, template))

    def _refresh_all_panels(self):
        self.project_panel.refresh()
        self.endpoint_panel.refresh()
        self.message_editor.refresh()
        self.template_panel.refresh()
        self.scenario_panel.refresh()
        self._repopulate_cont_report_combo()

    def _repopulate_cont_report_combo(self):
        self.cont_report_combo.clear()
        project = self.project_manager.current_project
        if not project:
            return
        report_cats = (
            "report_device_status", "report_alarm", "report_img",
            "report_high_range", "report_range_result", "report_task",
            "heartbeat",
        )
        self.cont_report_combo.addItem("-- 选择上报模板 --", "")
        active_ep_ids = getattr(self, "_active_env_endpoint_ids", [])
        for t in project.message_templates:
            if t.category.value in report_cats:
                if active_ep_ids and t.endpoint_id and t.endpoint_id not in active_ep_ids:
                    continue
                label = f"[{t.category.value}] {t.name}"
                self.cont_report_combo.addItem(label, t.id)

    def _on_continuous_report_toggled(self, checked: bool):
        if checked:
            template_id = self.cont_report_combo.currentData()
            if not template_id:
                self.cont_report_btn.setChecked(False)
                QMessageBox.warning(self, "提示", "请先选择一个上报模板")
                return
            endpoint_id = self._get_first_running_endpoint_id()
            if not endpoint_id:
                self.cont_report_btn.setChecked(False)
                QMessageBox.warning(self, "提示", "请先启动至少一个 TCP 端点")
                return
            interval_ms = self.cont_report_interval.value() * 1000
            self._cont_report_timer.start(interval_ms)
            self.cont_report_btn.setText("⏸ 停止上报")
            self.cont_report_combo.setEnabled(False)
            self.cont_report_interval.setEnabled(False)
            self.logger.info(f"持续上报已启动: 间隔 {self.cont_report_interval.value()}s")
        else:
            self._cont_report_timer.stop()
            self.cont_report_btn.setText("▶ 开始上报")
            self.cont_report_combo.setEnabled(True)
            self.cont_report_interval.setEnabled(True)
            self.logger.info(f"持续上报已停止, 共上报 {self._cont_report_count} 次")
            self._cont_report_count = 0
            self.cont_report_count_label.setText(" 0")

    def _do_continuous_report(self):
        template_id = self.cont_report_combo.currentData()
        if not template_id:
            return
        endpoint_id = self._get_first_running_endpoint_id()
        if not endpoint_id:
            self.cont_report_btn.setChecked(False)
            return
        project = self.project_manager.current_project
        if not project:
            return
        for t in project.message_templates:
            if t.id == template_id:
                self._cont_report_count += 1
                self.cont_report_count_label.setText(f" {self._cont_report_count}")
                asyncio.create_task(self.runtime_manager.send_message(endpoint_id, t))
                return

    def _get_first_running_endpoint_id(self) -> str:
        for ep_id, adapter in self.runtime_manager._transports.items():
            if adapter.is_running():
                return ep_id
        return ""

    def closeEvent(self, event):
        if self.project_manager.current_project:
            try:
                self.project_manager.save_project()
                self.logger.info("自动保存项目完成")
            except Exception as e:
                self.logger.warn(f"自动保存失败: {e}")
        asyncio.create_task(self.runtime_manager.stop_all())
        self.logger.close()
        event.accept()
        QApplication.quit()
