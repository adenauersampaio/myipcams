import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie, QPixmap, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from .assets import get_app_icon, get_camera_animation_path, get_asset_path, get_project_root


class AboutDialog(QDialog):
    """Diálogo 'Sobre o MyIPCams' com animação da câmera e informações do aplicativo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o MyIPCams")
        self.setWindowIcon(get_app_icon())
        self.setFixedSize(520, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #121418;
            }
            QLabel {
                color: #E2E8F0;
            }
            QFrame#cardFrame {
                background-color: #181B22;
                border: 1px solid #2D3748;
                border-radius: 10px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Container superior com a animação da câmera
        anim_container = QFrame()
        anim_container.setObjectName("cardFrame")
        anim_layout = QVBoxLayout(anim_container)
        anim_layout.setContentsMargins(8, 8, 8, 8)
        anim_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.movie_label = QLabel()
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_label.setStyleSheet("border-radius: 8px; background-color: #0B0D11;")

        anim_path = get_camera_animation_path()
        if anim_path and os.path.exists(anim_path):
            self.movie = QMovie(anim_path)
            # Redimensiona mantendo proporção (ex: 360 x 202)
            self.movie.setScaledSize(QSize(360, 202))
            self.movie_label.setMovie(self.movie)
            self.movie.start()
        else:
            icon_path = get_asset_path("icon_256.png") or get_asset_path("myipcams.png")
            if icon_path:
                pixmap = QPixmap(str(icon_path)).scaled(
                    128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                self.movie_label.setPixmap(pixmap)
            self.movie = None

        anim_layout.addWidget(self.movie_label)
        layout.addWidget(anim_container)

        # Informações do Aplicativo
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_label = QLabel()
        small_icon_path = get_asset_path("icon_48.png") or get_asset_path("myipcams.png")
        if small_icon_path:
            icon_label.setPixmap(QPixmap(str(small_icon_path)).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_lbl = QLabel("<b>MyIPCams</b> <span style='color: #38BDF8;'>v0.1.0</span>")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        sub_lbl = QLabel("Visualizador de Câmeras IP com Rastreamento Dinâmico de IPs")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_layout.addWidget(title_lbl)
        title_layout.addWidget(sub_lbl)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Descrição e recursos
        features_frame = QFrame()
        features_frame.setObjectName("cardFrame")
        features_layout = QVBoxLayout(features_frame)
        features_layout.setSpacing(6)
        features_layout.setContentsMargins(12, 10, 12, 10)

        desc_lbl = QLabel(
            "• Rastreamento automático de IPs via ARP & ONVIF WS-Discovery\n"
            "• Suporte a câmeras ONVIF, Xiongmai (XM/ICSee) e RTSP genérico\n"
            "• Controle PTZ integrado (Pan/Tilt/Zoom e Presets)\n"
            "• Monitoramento contínuo em segundo plano para redes DHCP dinâmicas"
        )
        desc_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; line-height: 1.4;")
        features_layout.addWidget(desc_lbl)
        layout.addWidget(features_frame)

        # Botões na parte inferior
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_folder = QPushButton("📁 Abrir Pasta do App")
        btn_folder.setObjectName("secondaryBtn")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self._open_project_folder)
        btn_layout.addWidget(btn_folder)

        btn_layout.addStretch()

        btn_close = QPushButton("Fechar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _open_project_folder(self):
        project_dir = get_project_root()
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(project_dir)))

    def closeEvent(self, event):
        if hasattr(self, "movie") and self.movie:
            self.movie.stop()
        super().closeEvent(event)
