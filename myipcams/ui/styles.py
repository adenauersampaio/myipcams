DARK_THEME_QSS = """
QMainWindow {
    background-color: #121418;
}

QWidget {
    background-color: #121418;
    color: #E2E8F0;
    font-size: 13px;
}

/* ToolBar */
QToolBar {
    background-color: #1A1D24;
    border-bottom: 1px solid #2D3748;
    padding: 6px;
    spacing: 8px;
}

QToolButton {
    background-color: #242933;
    color: #F8FAFC;
    border: 1px solid #3E4C5F;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #2E3846;
    border-color: #4A90E2;
}

QToolButton:pressed {
    background-color: #1E252F;
}

/* Botões Gerais */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton#secondaryBtn {
    background-color: #2D3748;
    color: #E2E8F0;
    border: 1px solid #4A5568;
}

QPushButton#secondaryBtn:hover {
    background-color: #374151;
}

QPushButton#dangerBtn {
    background-color: #DC2626;
}

QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
}

/* Botões de Ação da Câmera (Cards) */
QPushButton#camActionBtn {
    background-color: #1E232D;
    color: #E2E8F0;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 0px;
    margin: 0px;
    font-size: 13px;
    font-weight: normal;
}

QPushButton#camActionBtn:hover {
    background-color: #2D3748;
    border-color: #3B82F6;
    color: #FFFFFF;
}

QPushButton#camActionBtn:pressed {
    background-color: #1E40AF;
}

/* Diálogos e Menus */
QDialog {
    background-color: #181B22;
}

QMenu {
    background-color: #1E232D;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2563EB;
}

/* Inputs */
QLineEdit, QSpinBox, QComboBox {
    background-color: #1E232D;
    color: #F8FAFC;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}

/* Botões internos de inputs (ex: alternador de visibilidade de senha) */
QLineEdit QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    margin: 0px 2px;
}

QLineEdit QToolButton:hover {
    background-color: #2D3748;
    border-color: transparent;
}

QLineEdit QToolButton:pressed {
    background-color: #374151;
}

/* Tabelas e Listas */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #161920;
    border: 1px solid #2D3748;
    border-radius: 6px;
    gridline-color: #242B38;
}

QHeaderView::section {
    background-color: #1F242F;
    color: #94A3B8;
    padding: 6px;
    border: 1px solid #2D3748;
    font-weight: bold;
}

QStatusBar {
    background-color: #161920;
    border-top: 1px solid #242B38;
    color: #94A3B8;
    font-size: 12px;
}

/* Alças de Redimensionamento Livre (QSplitter) */
QSplitter::handle {
    background-color: #121418;
}

QSplitter::handle:horizontal {
    width: 6px;
}

QSplitter::handle:vertical {
    height: 6px;
}

QSplitter::handle:hover {
    background-color: #3B82F6;
}

QSplitter::handle:pressed {
    background-color: #1D4ED8;
}
"""
