from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSlider,
)


class PTZPanel(QFrame):
    """Painel HUD flutuante de controle PTZ (D-Pad) sobreposto ao vídeo da câmera.
    
    Compacto, semitransparente e sem deformar a proporção do vídeo.
    """

    move_requested = pyqtSignal(str, int)  # (direction, speed)
    stop_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed = 4
        self.setFixedSize(140, 142)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("ptzPanel")
        self.setStyleSheet("""
            QFrame#ptzPanel {
                background-color: rgba(18, 22, 30, 0.93);
                border: 1px solid #3B82F6;
                border-radius: 8px;
            }
            QPushButton.ptzDirBtn {
                background-color: #1E232D;
                color: #F3F4F6;
                border: 1px solid #374151;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 26px;
                max-height: 26px;
                padding: 0px;
            }
            QPushButton.ptzDirBtn:hover {
                background-color: #2563EB;
                border-color: #60A5FA;
                color: #FFFFFF;
            }
            QPushButton.ptzDirBtn:pressed {
                background-color: #1D4ED8;
            }
            QPushButton#ptzCloseBtn {
                background-color: transparent;
                color: #9CA3AF;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#ptzCloseBtn:hover {
                color: #EF4444;
            }
            QLabel {
                color: #94A3B8;
                font-size: 10px;
                font-weight: bold;
            }
            QSlider::groove:horizontal {
                height: 3px;
                background: #374151;
                border-radius: 1px;
            }
            QSlider::sub-page:horizontal {
                background: #3B82F6;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #60A5FA;
                width: 8px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 4px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(2)

        # 1. Barra superior: Título, Slider de Velocidade e Botão Fechar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(4)

        title_label = QLabel("🎮 PTZ")
        top_bar.addWidget(title_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 8)
        self.speed_slider.setValue(4)
        self.speed_slider.setMaximumWidth(45)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        top_bar.addWidget(self.speed_slider)

        self.lbl_speed_val = QLabel("4")
        self.lbl_speed_val.setStyleSheet("color: #60A5FA; font-weight: bold; font-size: 10px;")
        top_bar.addWidget(self.lbl_speed_val)

        top_bar.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("ptzCloseBtn")
        self.btn_close.setFixedSize(16, 16)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_requested.emit)
        top_bar.addWidget(self.btn_close)

        main_layout.addLayout(top_bar)

        # 2. Grade de Botões Direcionais (D-Pad)
        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setContentsMargins(0, 2, 0, 2)

        self.btn_up = QPushButton("↑")
        self.btn_up.setProperty("class", "ptzDirBtn")
        self.btn_up.setToolTip("Mover para Cima")
        self._bind_button(self.btn_up, "up")

        self.btn_down = QPushButton("↓")
        self.btn_down.setProperty("class", "ptzDirBtn")
        self.btn_down.setToolTip("Mover para Baixo")
        self._bind_button(self.btn_down, "down")

        self.btn_left = QPushButton("←")
        self.btn_left.setProperty("class", "ptzDirBtn")
        self.btn_left.setToolTip("Mover para Esquerda")
        self._bind_button(self.btn_left, "left")

        self.btn_right = QPushButton("→")
        self.btn_right.setProperty("class", "ptzDirBtn")
        self.btn_right.setToolTip("Mover para Direita")
        self._bind_button(self.btn_right, "right")

        self.btn_stop = QPushButton("■")
        self.btn_stop.setProperty("class", "ptzDirBtn")
        self.btn_stop.setToolTip("Parar Movimento")
        self.btn_stop.clicked.connect(lambda: self.stop_requested.emit())

        grid.addWidget(self.btn_up, 0, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.btn_left, 1, 0, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.btn_stop, 1, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.btn_right, 1, 2, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.btn_down, 2, 1, Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(grid)

    def _bind_button(self, btn: QPushButton, direction: str):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.pressed.connect(lambda: self.move_requested.emit(direction, self._speed))
        btn.released.connect(self.stop_requested.emit)

    def _on_speed_changed(self, val: int):
        self._speed = val
        self.lbl_speed_val.setText(str(val))


# Alias para retrocompatibilidade
PTZOverlay = PTZPanel
