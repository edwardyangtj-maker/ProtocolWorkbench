DARK_THEME_QSS = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    border: none;
}

QMainWindow {
    background-color: #1e1e2e;
}

QSplitter::handle {
    background-color: #313244;
    width: 2px;
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #89b4fa;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}

QMenuBar::item {
    padding: 6px 14px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #313244;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 28px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #313244;
}

QMenu::separator {
    height: 1px;
    background: #313244;
    margin: 4px 8px;
}

QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}

QToolButton:hover {
    background-color: #313244;
}

QToolButton:pressed {
    background-color: #45475a;
}

QToolButton:checked {
    background-color: #313244;
    color: #89b4fa;
}

QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
    top: -1px;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 2px;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}

QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

QTreeWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    outline: none;
    alternate-background-color: #1e1e2e;
}

QTreeWidget::item {
    padding: 4px 8px;
    border-radius: 3px;
}

QTreeWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}

QTreeWidget::item:hover:!selected {
    background-color: #252536;
}

QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    border-right: 1px solid #313244;
    border-bottom: 1px solid #313244;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: bold;
}

QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    outline: none;
    alternate-background-color: #1e1e2e;
}

QTableWidget::item {
    padding: 4px 8px;
}

QTableWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}

QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    selection-background-color: #313244;
    selection-color: #89b4fa;
    padding: 4px;
    font-family: "Cascadia Code", "Consolas", "Microsoft YaHei", monospace;
    font-size: 13px;
}

QLineEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #313244;
}

QLineEdit:focus {
    border-color: #89b4fa;
}

QComboBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 80px;
}

QComboBox:hover {
    border-color: #585b70;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #a6adc8;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    selection-background-color: #313244;
    selection-color: #89b4fa;
    outline: none;
}

QSpinBox, QDoubleSpinBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px 8px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #89b4fa;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}

QPushButton:pressed {
    background-color: #585b70;
    padding-top: 9px;
    padding-bottom: 5px;
    border-color: #89b4fa;
}

QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}

QPushButton[class="primary"] {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
}

QPushButton[class="primary"]:hover {
    background-color: #74c7ec;
}

QPushButton[class="primary"]:pressed {
    background-color: #5b9bd5;
    padding-top: 9px;
    padding-bottom: 5px;
}

QPushButton[class="danger"] {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
}

QPushButton[class="danger"]:hover {
    background-color: #eba0ac;
}

QPushButton[class="danger"]:pressed {
    background-color: #d6607e;
    padding-top: 9px;
    padding-bottom: 5px;
}

QPushButton[class="success"] {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
}

QPushButton[class="success"]:hover {
    background-color: #94e2d5;
}

QPushButton[class="success"]:pressed {
    background-color: #7dc4b5;
    padding-top: 9px;
    padding-bottom: 5px;
}

QPushButton[class="warning"] {
    background-color: #f9e2af;
    color: #1e1e2e;
    border: none;
}

QPushButton[class="warning"]:hover {
    background-color: #fab387;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #585b70;
    background-color: #181825;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

QGroupBox {
    color: #a6adc8;
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
}

QLabel {
    color: #cdd6f4;
    background: transparent;
}

QLabel[class="title"] {
    color: #89b4fa;
    font-size: 15px;
    font-weight: bold;
}

QLabel[class="subtitle"] {
    color: #a6adc8;
    font-size: 12px;
}

QLabel[class="status_idle"] {
    color: #a6adc8;
}

QLabel[class="status_running"] {
    color: #a6e3a1;
}

QLabel[class="status_error"] {
    color: #f38ba8;
}

QFrame[class="card"] {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
}

QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 6px 10px;
    border-radius: 3px;
}

QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}

QListWidget::item:hover:!selected {
    background-color: #252536;
}

QToolTip {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 4px 8px;
}

QDialog {
    background-color: #1e1e2e;
}
"""
