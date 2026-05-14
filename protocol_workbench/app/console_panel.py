from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QComboBox,
)

from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench import __version__


class ConsolePanel(QWidget):
    def __init__(self, logger: LoggerService, parent=None):
        super().__init__(parent)
        self.logger = logger
        self._command_history: list[str] = []
        self._history_index = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)
        label = QLabel("🖥 命令控制台")
        label.setProperty("class", "title")
        toolbar.addWidget(label)

        hint = QLabel("输入 help 查看可用命令 | Enter 执行 | ↑↓ 翻历史")
        hint.setProperty("class", "subtitle")
        toolbar.addWidget(hint, 1)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)
        layout.addLayout(toolbar)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Cascadia Code", 11))
        self.output.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.output)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(8, 4, 8, 4)

        prompt_label = QLabel(">")
        prompt_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 16px;")
        input_layout.addWidget(prompt_label)

        self.input_combo = QComboBox()
        self.input_combo.setEditable(True)
        self.input_combo.setMinimumWidth(300)
        self.input_combo.setPlaceholderText("输入命令... (help 查看帮助)")
        line_edit = self.input_combo.lineEdit()
        line_edit.returnPressed.connect(self._execute)
        input_layout.addWidget(self.input_combo, 1)

        self.run_btn = QPushButton("▶ 执行")
        self.run_btn.setProperty("class", "primary")
        self.run_btn.clicked.connect(self._execute)
        input_layout.addWidget(self.run_btn)

        layout.addLayout(input_layout)

        self._show_welcome()

    def _show_welcome(self):
        welcome = """
<span style="color:#89b4fa;font-size:14px;font-weight:bold">🖥 Protocol Workbench 命令控制台</span>
<span style="color:#a6adc8">用于快速查看项目状态、执行调试命令</span>
<span style="color:#f9e2af">输入 <b>help</b> 查看所有可用命令</span>
"""
        self.output.append(welcome)

    def _execute(self):
        cmd = self.input_combo.currentText().strip()
        if not cmd:
            return

        self.output.append(f'<span style="color:#89b4fa">&gt; {cmd}</span>')
        self._command_history.append(cmd)
        self._history_index = len(self._command_history)
        self.input_combo.setCurrentText("")

        try:
            parts = cmd.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if command == "help":
                self._show_help()
            elif command == "clear":
                self.output.clear()
                self._show_welcome()
            elif command == "list":
                self._handle_list(args)
            elif command == "send":
                self.output.append(f'<span style="color:#f9e2af">提示: 发送功能请使用端点面板的发送按钮</span>')
            elif command == "status":
                self._show_status()
            elif command == "version":
                self.output.append(f'<span style="color:#a6e3a1">Protocol Workbench v{__version__}</span>')
            elif command == "history":
                self._show_history()
            else:
                self.output.append(f'<span style="color:#f38ba8">未知命令: {cmd}</span>')
                self.output.append(f'<span style="color:#a6adc8">输入 help 查看可用命令</span>')
        except Exception as e:
            self.output.append(f'<span style="color:#f38ba8">错误: {e}</span>')

    def _show_help(self):
        help_text = """
<span style="color:#f9e2af;font-weight:bold">可用命令:</span>
<span style="color:#89b4fa">help</span>              - 显示此帮助信息
<span style="color:#89b4fa">clear</span>             - 清空控制台
<span style="color:#89b4fa">list endpoints</span>    - 列出所有端点及状态
<span style="color:#89b4fa">list templates</span>    - 列出所有消息模板
<span style="color:#89b4fa">list scenarios</span>    - 列出所有场景
<span style="color:#89b4fa">list environments</span> - 列出所有环境
<span style="color:#89b4fa">status</span>            - 显示当前项目状态
<span style="color:#89b4fa">version</span>           - 显示版本信息
<span style="color:#89b4fa">history</span>           - 显示命令历史
<span style="color:#a6adc8">提示: 使用 ↑↓ 键浏览历史命令</span>
"""
        self.output.append(help_text)

    def _handle_list(self, args: str):
        app_window = self.window()
        if not hasattr(app_window, 'project_manager'):
            self.output.append('<span style="color:#f38ba8">无法访问项目管理器</span>')
            return

        project = app_window.project_manager.current_project
        if not project:
            self.output.append('<span style="color:#f9e2af">当前没有打开的项目</span>')
            return

        if args == "endpoints":
            self.output.append('<span style="color:#f9e2af;font-weight:bold">端点列表:</span>')
            for ep in project.endpoints:
                state = app_window.runtime_manager.get_endpoint_state(ep.id) if hasattr(app_window, 'runtime_manager') else "unknown"
                state_icon = {"idle": "⏸", "connected": "🟢", "listening": "🟢", "error": "❌"}.get(state, "❓")
                self.output.append(f'  {state_icon} <b>{ep.name}</b> ({ep.type.value}) {ep.host}:{ep.port}')
        elif args == "templates":
            self.output.append('<span style="color:#f9e2af;font-weight:bold">模板列表:</span>')
            for tpl in project.message_templates:
                self.output.append(f'  📄 <b>{tpl.name}</b> ({tpl.category.value}, {tpl.payload_type.value})')
        elif args == "scenarios":
            self.output.append('<span style="color:#f9e2af;font-weight:bold">场景列表:</span>')
            for sc in project.scenarios:
                self.output.append(f'  🎬 <b>{sc.name}</b> ({len(sc.steps)} 步骤)')
        elif args == "environments":
            self.output.append('<span style="color:#f9e2af;font-weight:bold">环境列表:</span>')
            for env in project.environments:
                self.output.append(f'  🏠 <b>{env.name}</b> ({len(env.endpoint_ids)} 端点, {len(env.variables)} 变量)')
        else:
            self.output.append(f'<span style="color:#a6adc8">用法: list [endpoints|templates|scenarios|environments]</span>')

    def _show_status(self):
        app_window = self.window()
        if not hasattr(app_window, 'project_manager'):
            self.output.append('<span style="color:#f38ba8">无法访问项目管理器</span>')
            return
        project = app_window.project_manager.current_project
        if not project:
            self.output.append('<span style="color:#f9e2af">当前没有打开的项目</span>')
            return
        running = 0
        if hasattr(app_window, 'runtime_manager'):
            for ep in project.endpoints:
                state = app_window.runtime_manager.get_endpoint_state(ep.id)
                if state in ("connected", "listening"):
                    running += 1
        self.output.append(f'<span style="color:#a6e3a1">项目: {project.name}</span>')
        self.output.append(f'  端点: {len(project.endpoints)} (运行中: {running})')
        self.output.append(f'  模板: {len(project.message_templates)}')
        self.output.append(f'  场景: {len(project.scenarios)}')
        self.output.append(f'  环境: {len(project.environments)}')

    def _show_history(self):
        if not self._command_history:
            self.output.append('<span style="color:#a6adc8">无历史命令</span>')
            return
        self.output.append('<span style="color:#f9e2af">命令历史:</span>')
        for i, cmd in enumerate(self._command_history[-20:], 1):
            self.output.append(f'  {i}. {cmd}')

    def _clear(self):
        self.output.clear()
        self._show_welcome()
