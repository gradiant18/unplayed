from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QPushButton


THEME = """
QWidget {
    background-color: #121417;
    color: #E6EDF3;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame {
    border: none;
}

QDialog, QMessageBox {
    background-color: #161B22;
}

QMessageBox QLabel {
    background-color: transparent;
    color: #E6EDF3;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #282E39;
    background-color: #161B22;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #0D1117;
    color: #8B949E;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #21262D;
    border-bottom: none;
    font-weight: 600;
}

QTabBar::tab:hover {
    background-color: #1F242C;
    color: #C9D1D9;
}

QTabBar::tab:selected {
    background-color: #161B22;
    color: #58A6FF;
    border-top: 2px solid #58A6FF;
}

QLineEdit, QComboBox, QSpinBox, QDateTimeEdit, QTimeEdit, QTextEdit {
    background-color: #0D1117;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 5px 8px;
    color: #F0F6FC;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateTimeEdit:focus, QTimeEdit:focus, QTextEdit:focus {
    border: 1px solid #58A6FF;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDateTimeEdit:disabled, QTimeEdit:disabled {
    background-color: #161B22;
    color: #484F58;
    border-color: #21262D;
}

QComboBox QAbstractItemView {
    background-color: #161B22;
    border: 1px solid #30363D;
    selection-background-color: #1F6FEB;
    selection-color: #FFFFFF;
}

QCheckBox {
    spacing: 8px;
    color: #C9D1D9;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #30363D;
    background-color: #0D1117;
}

QCheckBox::indicator:hover {
    border-color: #58A6FF;
}

QCheckBox::indicator:checked {
    background-color: #1F6FEB;
    border-color: #58A6FF;
}

QPushButton {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
    padding: 6px 16px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #30363D;
    border-color: #8B949E;
}

QPushButton:pressed {
    background-color: #161B22;
}

QMessageBox QPushButton {
    min-width: 70px;
    padding: 6px 14px;
}

QPushButton#btn_start {
    background-color: #238636;
    color: #FFFFFF;
    border: 1px solid #2EA043;
    font-size: 14px;
    font-weight: bold;
    padding: 8px;
}
QPushButton#btn_start:hover { background-color: #2EA043; }

QPushButton#btn_reload { background-color: #D29922; color: #FFFFFF; border: 1px solid #E3B341; }
QPushButton#btn_reload:hover { background-color: #E3B341; }

QPushButton#btn_skip { background-color: #DB6D28; color: #FFFFFF; border: 1px solid #F0883E; }
QPushButton#btn_skip:hover { background-color: #F0883E; }

QPushButton#btn_stop { background-color: #DA3633; color: #FFFFFF; border: 1px solid #F85149; }
QPushButton#btn_stop:hover { background-color: #F85149; }

QScrollBar:vertical {
    background-color: #0D1117;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #30363D;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #58A6FF;
}

QScrollBar::handle:vertical:pressed {
    background-color: #1F6FEB;
}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical,
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0D1117;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #30363D;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #58A6FF;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #1F6FEB;
}

QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal,
QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    border: none;
    width: 0px;
}

QProgressBar {
    border: 1px solid #30363D;
    border-radius: 6px;
    background-color: #0D1117;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1F6FEB, stop:1 #58A6FF);
    border-radius: 5px;
}

QStatusBar {
    background-color: #0D1117;
    color: #8B949E;
    border-top: 1px solid #21262D;
}"""


class _DialogButtonCleanFilter(QObject):
    def eventFilter(self, obj, event):
        show_event = getattr(QEvent.Type, "Show", None) or getattr(QEvent, "Show", None)
        if event.type() == show_event:
            for btn in obj.findChildren(QPushButton):
                btn.setIcon(QIcon())
        return super().eventFilter(obj, event)


def apply_theme(app):
    """Applies the dark theme stylesheet and removes washed-out OS icons from dialogs."""
    global _filter_instance

    attr = getattr(Qt.ApplicationAttribute, "AA_DontShowIconsInMenus", None) or getattr(
        Qt, "AA_DontShowIconsInMenus", None
    )
    app.setAttribute(attr, True)
    _filter_instance = _DialogButtonCleanFilter()
    app.installEventFilter(_filter_instance)
    app.setStyleSheet(THEME)
