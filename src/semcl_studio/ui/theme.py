from __future__ import annotations


COLORS = {
    "primary": "#0066cc",
    "primary_focus": "#0071e3",
    "ink": "#1d1d1f",
    "muted": "#6e6e73",
    "canvas": "#ffffff",
    "parchment": "#f5f5f7",
    "pearl": "#fafafc",
    "hairline": "#e0e0e0",
    "selection": "#e8f2ff",
}


APP_STYLESHEET = f"""
QWidget {{
    background: {COLORS['canvas']};
    color: {COLORS['ink']};
    font-family: "Segoe UI";
    font-size: 13px;
}}
QMainWindow, QMenuBar, QMenu, QStatusBar {{
    background: {COLORS['canvas']};
}}
QMenuBar {{
    border-bottom: 1px solid {COLORS['hairline']};
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background: {COLORS['selection']};
    color: {COLORS['primary']};
}}
QFrame#TopBar {{
    background: rgba(245, 245, 247, 230);
    border-bottom: 1px solid {COLORS['hairline']};
}}
QFrame#FilePanel, QFrame#InspectorPanel {{
    background: {COLORS['parchment']};
    border-right: 1px solid {COLORS['hairline']};
}}
QLabel#AppTitle {{
    font-size: 18px;
    font-weight: 600;
}}
QLabel#SectionTitle {{
    font-size: 12px;
    font-weight: 600;
    color: #3a3a3c;
}}
QLabel#MutedLabel {{
    color: {COLORS['muted']};
}}
QPushButton {{
    min-height: 30px;
    padding: 3px 11px;
    border: 1px solid {COLORS['hairline']};
    border-radius: 8px;
    background: {COLORS['canvas']};
}}
QPushButton:hover {{
    border-color: #b8b8bd;
    background: {COLORS['pearl']};
}}
QPushButton:pressed {{
    background: #eeeeF1;
}}
QPushButton:checked, QPushButton#PrimaryButton {{
    background: {COLORS['primary']};
    color: white;
    border-color: {COLORS['primary']};
}}
QPushButton#PrimaryButton:hover {{
    background: {COLORS['primary_focus']};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    min-height: 29px;
    padding: 1px 7px;
    border: 1px solid #d2d2d7;
    border-radius: 7px;
    background: {COLORS['canvas']};
    selection-background-color: {COLORS['primary']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {COLORS['primary_focus']};
}}
QListWidget, QTreeWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    min-height: 34px;
    padding: 4px 7px;
    border-radius: 7px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {COLORS['selection']};
    color: {COLORS['ink']};
}}
QTabWidget::pane {{
    border: none;
    background: {COLORS['canvas']};
}}
QTabBar::tab {{
    min-width: 100px;
    min-height: 38px;
    padding: 2px 12px;
    border: none;
    color: #515154;
}}
QTabBar::tab:selected {{
    color: {COLORS['primary']};
    font-weight: 600;
    border-bottom: 2px solid {COLORS['primary']};
}}
QGroupBox {{
    margin-top: 12px;
    padding-top: 10px;
    font-weight: 600;
    border: none;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 0px;
}}
QSplitter::handle {{
    background: {COLORS['hairline']};
    width: 1px;
    height: 1px;
}}
QScrollArea {{
    border: none;
    background: {COLORS['parchment']};
}}
QToolTip {{
    background: {COLORS['ink']};
    color: white;
    border: none;
    padding: 5px;
}}
"""
