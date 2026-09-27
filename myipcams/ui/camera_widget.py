import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont, QAction, QPainter
from PyQt6.QtWidgets import (
    QDialog,
    QLineEdit,
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QLabel,
    QPushButton,
    QMenu,
    QMessageBox,
    QSizePolicy,
)

from ..core.camera import Camera
from ..player.stream_worker import StreamWorker
from .ptz_overlay import PTZOverlay
from .xm_alarm_dialog import XMAlarmDialog
from ..network.xm_client import XMClient, probe_device
from ..network.onvif_ptz import ONVIFPTZClient


class ClickableNameLabel(QLabel):
    """Área do nome da câmera com suporte a duplo clique para renomear."""
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class CameraRenameDialog(QDialog):
    """Diálogo modal rápido para renomear uma câmera facilitando sua identificação."""

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Renomear Câmera")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("Digite um novo nome para facilitar a identificação da câmera:")
        lbl.setStyleSheet("font-weight: 500; font-size: 13px; color: #F8FAFC;")
        layout.addWidget(lbl)

        self.name_input = QLineEdit()
        self.name_input.setText(current_name)
        self.name_input.setPlaceholderText("Ex: Garagem, Portão, Entrada Principal...")
        self.name_input.selectAll()
        self.name_input.returnPressed.connect(self._save)
        layout.addWidget(self.name_input)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Salvar")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Aviso", "O nome da câmera não pode ficar em branco.")
            return
        self.accept()

    def get_name(self) -> str:
        return self.name_input.text().strip()


class VideoLabel(QLabel):
    """Área de exibição de vídeo com renderização mantendo proporção e expansão total."""

    def __init__(self, text: str = "Conectando...", parent=None):
        super().__init__(text, parent)
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 80)

    def set_frame(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.setText("")
        self.update()

    def clear_frame(self, text: str = "Sem Sinal (Offline)"):
        self._pixmap = None
        self.setText(text)
        self.update()

    def minimumSizeHint(self) -> QSize:
        return QSize(120, 80)

    def sizeHint(self) -> QSize:
        return QSize(320, 180)

    def paintEvent(self, event):
        if self._pixmap and not self._pixmap.isNull():
            painter = QPainter(self)
            target_rect = self.rect()
            scaled_size = self._pixmap.size().scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            x = target_rect.x() + (target_rect.width() - scaled_size.width()) // 2
            y = target_rect.y() + (target_rect.height() - scaled_size.height()) // 2
            painter.drawPixmap(x, y, scaled_size.width(), scaled_size.height(), self._pixmap)
            painter.end()
        else:
            super().paintEvent(event)


class CameraWidget(QFrame):
    """Widget de exibição individual de uma câmera com controle de stream e status."""

    double_clicked = pyqtSignal(str)   # emite camera_id ao dar duplo clique ou maximizar
    edit_requested = pyqtSignal(str)   # emite camera_id
    remove_requested = pyqtSignal(str) # emite camera_id
    reconnect_requested = pyqtSignal(str)
    camera_updated = pyqtSignal(str)   # emite camera_id quando as propriedades da câmera mudam

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.worker: Optional[StreamWorker] = None
        self.thread: Optional[QThread] = None
        self._is_maximized_in_grid = False
        self._xm_client: Optional[XMClient] = None
        self._onvif_client: Optional[ONVIFPTZClient] = None

        self._setup_ui()
        self.update_camera_info()
        self.start_stream()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 90)
        self.setStyleSheet("""
            CameraWidget {
                background-color: #0F1115;
                border: 2px solid #232832;
                border-radius: 8px;
            }
            CameraWidget:hover {
                border-color: #3B82F6;
            }
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
            QPushButton#camMaxBtn {
                background-color: #1E232D;
                color: #60A5FA;
                border: 1px solid #3B82F6;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#camMaxBtn:hover {
                background-color: #2563EB;
                border-color: #60A5FA;
                color: #FFFFFF;
            }
            QPushButton#camMaxBtn:pressed {
                background-color: #1D4ED8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 1. Barra de Cabeçalho Superior
        header = QHBoxLayout()
        header.setContentsMargins(6, 4, 6, 2)
        header.setSpacing(4)

        self.name_label = ClickableNameLabel(self.camera.name)
        self.name_label.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #FFFFFF;")
        self.name_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_label.setToolTip("Dê dois cliques para renomear a câmera")
        self.name_label.double_clicked.connect(self._rename_camera)

        self.btn_rename = QPushButton("✏️")
        self.btn_rename.setObjectName("camActionBtn")
        self.btn_rename.setToolTip("Renomear Câmera")
        self.btn_rename.setFixedSize(22, 20)
        self.btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rename.clicked.connect(self._rename_camera)

        self.ip_label = QLabel(self.camera.current_ip)
        self.ip_label.setStyleSheet("""
            background-color: #1E232D;
            color: #94A3B8;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
        """)

        self.status_badge = QLabel("Offline")
        self.status_badge.setStyleSheet("""
            background-color: #374151;
            color: #9CA3AF;
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: bold;
            font-size: 11px;
        """)

        # Botão de Maximizar / Restaurar com seta diagonal
        self.btn_maximize = QPushButton("↗")
        self.btn_maximize.setObjectName("camMaxBtn")
        self.btn_maximize.setToolTip("Maximizar Câmera na Tela (↗)")
        self.btn_maximize.setFixedSize(26, 22)
        self.btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_maximize.clicked.connect(self._on_maximize_clicked)

        header.addWidget(self.name_label)
        header.addWidget(self.btn_rename)
        header.addStretch()
        header.addWidget(self.ip_label)
        header.addWidget(self.status_badge)
        header.addWidget(self.btn_maximize)
        layout.addLayout(header)

        # 2. Área Central de Vídeo com Camada StackAll Segura
        self.video_container = QWidget(self)
        self.video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_stack = QStackedLayout(self.video_container)
        self.video_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.video_label = VideoLabel("Conectando...", self.video_container)
        self.video_label.setStyleSheet("""
            background-color: #050608;
            color: #4B5563;
            border-radius: 6px;
            font-size: 13px;
        """)
        self.video_stack.addWidget(self.video_label)

        # Camada superior de overlay para o HUD PTZ (sem deformar nem esmagar o vídeo)
        self.overlay_layer = QWidget(self.video_container)
        self.overlay_layer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay_layout = QHBoxLayout(self.overlay_layer)
        overlay_layout.setContentsMargins(6, 6, 6, 6)
        overlay_layout.addStretch()

        self.ptz_overlay = PTZOverlay(self.overlay_layer)
        self.ptz_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.ptz_overlay.move_requested.connect(self._on_ptz_move)
        self.ptz_overlay.stop_requested.connect(self._on_ptz_stop)
        self.ptz_overlay.close_requested.connect(self.ptz_overlay.hide)
        self.ptz_overlay.hide()
        overlay_layout.addWidget(self.ptz_overlay, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.video_stack.addWidget(self.overlay_layer)
        layout.addWidget(self.video_container, stretch=1)

        # 3. Barra Inferior de Ações
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 2, 4, 2)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #64748B; font-size: 10px;")

        self.btn_ptz = QPushButton("🎮")
        self.btn_ptz.setObjectName("camActionBtn")
        self.btn_ptz.setToolTip("Controle PTZ (Mover Câmera)")
        self.btn_ptz.setFixedSize(28, 24)
        self.btn_ptz.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ptz.clicked.connect(self._toggle_ptz)

        self.btn_snapshot = QPushButton("📸")
        self.btn_snapshot.setObjectName("camActionBtn")
        self.btn_snapshot.setToolTip("Tirar Foto (Snapshot)")
        self.btn_snapshot.setFixedSize(28, 24)
        self.btn_snapshot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snapshot.clicked.connect(self._take_snapshot)

        self.btn_reconnect = QPushButton("🔄")
        self.btn_reconnect.setObjectName("camActionBtn")
        self.btn_reconnect.setToolTip("Reconectar Câmera")
        self.btn_reconnect.setFixedSize(28, 24)
        self.btn_reconnect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reconnect.clicked.connect(self._restart_stream)

        self.btn_edit = QPushButton("⚙️")
        self.btn_edit.setObjectName("camActionBtn")
        self.btn_edit.setToolTip("Configurar Câmera")
        self.btn_edit.setFixedSize(28, 24)
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.camera.id))

        footer.addWidget(self.stats_label)
        footer.addStretch()
        footer.addWidget(self.btn_ptz)
        footer.addWidget(self.btn_snapshot)
        footer.addWidget(self.btn_reconnect)
        footer.addWidget(self.btn_edit)
        layout.addLayout(footer)

    def set_maximized_state(self, is_maximized: bool):
        """Atualiza o ícone e tooltip do botão de maximizar de acordo com o estado na grade."""
        self._is_maximized_in_grid = is_maximized
        if is_maximized:
            self.btn_maximize.setText("↙")
            self.btn_maximize.setToolTip("Restaurar Grade (↙)")
        else:
            self.btn_maximize.setText("↗")
            self.btn_maximize.setToolTip("Maximizar Câmera na Tela (↗)")

    def _on_maximize_clicked(self):
        self.double_clicked.emit(self.camera.id)

    def update_camera_info(self):
        """Atualiza os textos de cabeçalho e tooltip após edição ou mudança de IP."""
        self.name_label.setText(self.camera.name)
        self.ip_label.setText(self.camera.current_ip)
        
        has_ptz = (self.camera.camera_type == "icsee" or bool(self.camera.onvif_port))
        self.btn_ptz.setVisible(has_ptz)
        if not has_ptz and hasattr(self, "ptz_overlay"):
            self.ptz_overlay.hide()

        tooltip = [f"Nome: {self.camera.name}", f"IP: {self.camera.current_ip}"]
        if self.camera.mac_address:
            tooltip.append(f"MAC: {self.camera.mac_address}")
        if self.camera.vendor_model:
            tooltip.append(f"Modelo: {self.camera.vendor_model}")
        tooltip.append(f"RTSP: {self.camera.rtsp_path}")
        if self.camera.camera_type == "icsee":
            tooltip.append("Recursos: iCSee / Xiongmai (PTZ + Alarmes)")
        elif self.camera.onvif_port:
            tooltip.append(f"Recursos: ONVIF (Porta {self.camera.onvif_port} + PTZ)")
        self.setToolTip("\n".join(tooltip))

    def on_ip_updated(self, new_ip: str):
        """Chamado quando o IPTracker detecta mudança no IP desta câmera."""
        self.ip_label.setText(new_ip)
        self.update_camera_info()
        new_url = self.camera.get_rtsp_url()
        if self.worker:
            self.worker.set_url(new_url)

    def start_stream(self):
        """Inicia a thread de captura de vídeo para a URL RTSP."""
        if not self.camera.enabled:
            self._set_status("offline")
            self.video_label.clear_frame("Câmera Desativada")
            return

        self.stop_stream()

        rtsp_url = self.camera.get_rtsp_url()
        self.thread = QThread()
        self.worker = StreamWorker(rtsp_url)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.status_changed.connect(self._set_status)
        self.worker.stats_updated.connect(self._on_stats_updated)

        self.thread.start()

    def stop_stream(self):
        """Finaliza a thread de captura com segurança."""
        if self.worker:
            self.worker.stop()
            self.worker = None
        if self.thread:
            self.thread.quit()
            if not self.thread.wait(1500):
                try:
                    self.thread.terminate()
                    self.thread.wait(500)
                except Exception:
                    pass
            self.thread = None

    def _restart_stream(self):
        self.video_label.clear_frame("Reconectando...")
        self.start_stream()

    def _on_frame_ready(self, q_img: QImage):
        """Renderiza o frame mantendo a proporção de aspecto (Aspect Ratio)."""
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.set_frame(pixmap)

    def _on_stats_updated(self, fps: float, width: int, height: int):
        self.stats_label.setText(f"{fps:.1f} fps | {width}x{height}")

    def _set_status(self, status: str):
        self.camera.status = status
        if status == "online":
            self.status_badge.setText("Online")
            self.status_badge.setStyleSheet("""
                background-color: #065F46;
                color: #34D399;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: bold;
                font-size: 11px;
            """)
        elif status == "reconnecting":
            self.status_badge.setText("Reconectando...")
            self.status_badge.setStyleSheet("""
                background-color: #78350F;
                color: #FBBF24;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: bold;
                font-size: 11px;
            """)
            self.video_label.clear_frame("Reconectando...")
        else:
            self.status_badge.setText("Offline")
            self.status_badge.setStyleSheet("""
                background-color: #374151;
                color: #9CA3AF;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: bold;
                font-size: 11px;
            """)
            self.video_label.clear_frame("Sem Sinal (Offline)")
            self.stats_label.setText("")

    def _take_snapshot(self):
        """Salva uma captura de tela na pasta de Imagens."""
        pictures_dir = Path.home() / "Pictures" / "myipcams"
        pictures_dir.mkdir(parents=True, exist_ok=True)
        filename = f"snapshot_{self.camera.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = str(pictures_dir / filename)

        if self.worker:
            self.worker.request_snapshot(filepath)
            QMessageBox.information(
                self,
                "Foto Capturada",
                f"Captura salva em:\n{filepath}"
            )
        else:
            QMessageBox.warning(self, "Aviso", "Câmera não está transmitindo no momento.")

    def mouseDoubleClickEvent(self, event):
        """Duplo clique maximiza/restaura a câmera na grade."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.camera.id)
        super().mouseDoubleClickEvent(event)

    def _get_xm_client(self) -> XMClient:
        if (
            self._xm_client is None
            or self._xm_client.ip != self.camera.current_ip
            or self._xm_client.port != self.camera.xm_port
            or self._xm_client.password != self.camera.password
            or self._xm_client.username != self.camera.username
        ):
            self._xm_client = XMClient(
                ip=self.camera.current_ip,
                port=self.camera.xm_port,
                username=self.camera.username,
                password=self.camera.password,
                timeout=2.5,
            )
        return self._xm_client

    def _get_onvif_client(self) -> Optional[ONVIFPTZClient]:
        port = self.camera.onvif_port or 80
        if (
            self._onvif_client is None
            or self._onvif_client.ip != self.camera.current_ip
            or self._onvif_client.port != port
            or self._onvif_client.password != self.camera.password
            or self._onvif_client.username != self.camera.username
        ):
            self._onvif_client = ONVIFPTZClient(
                ip=self.camera.current_ip,
                port=port,
                username=self.camera.username,
                password=self.camera.password,
                timeout=2.5,
            )
        return self._onvif_client

    def _toggle_ptz(self):
        vis = not self.ptz_overlay.isVisible()
        self.ptz_overlay.setVisible(vis)

    def _on_ptz_move(self, direction: str, speed: int):
        def _move():
            success = False
            # 1. Tenta protocolo Xiongmai Sofia
            if self.camera.camera_type == "icsee":
                try:
                    client = self._get_xm_client()
                    success = client.ptz_control(direction, speed)
                except Exception:
                    success = False

            # 2. Se falhou ou não é modo exclusivo icsee, tenta ONVIF PTZ
            if not success:
                try:
                    onvif = self._get_onvif_client()
                    if onvif:
                        onvif.move(direction, speed)
                except Exception:
                    pass

        threading.Thread(target=_move, daemon=True).start()

    def _on_ptz_stop(self):
        def _stop():
            if self.camera.camera_type == "icsee":
                try:
                    client = self._get_xm_client()
                    client.ptz_stop()
                except Exception:
                    pass

            try:
                onvif = self._get_onvif_client()
                if onvif:
                    onvif.stop()
            except Exception:
                pass

        threading.Thread(target=_stop, daemon=True).start()

    def _open_alarm_dialog(self):
        dlg = XMAlarmDialog(self.camera, self)
        dlg.exec()

    def _detect_and_activate_icsee(self):
        ip = self.camera.current_ip
        port = self.camera.xm_port or 34567
        if probe_device(ip, port=port, timeout=1.5):
            self.camera.camera_type = "icsee"
            self.update_camera_info()
            self.camera_updated.emit(self.camera.id)
            QMessageBox.information(
                self,
                "Recursos iCSee Detectados",
                f"A câmera '{self.camera.name}' ({ip}) respondeu com sucesso na porta {port}!\n\n"
                "O modo 'iCSee / Xiongmai' foi ativado com sucesso.\n"
                "O botão de controle PTZ (🎮) agora está disponível na barra inferior e no menu da câmera."
            )
        else:
            QMessageBox.information(
                self,
                "Não Detectado",
                f"A câmera '{self.camera.name}' ({ip}) não respondeu na porta {port} do protocolo iCSee.\n\n"
                "Ela continuará operando normalmente no modo Genérica (RTSP/ONVIF)."
            )

    def _rename_camera(self):
        """Abre diálogo rápido para editar o nome da câmera e salva as alterações."""
        dlg = CameraRenameDialog(self.camera.name, self)
        if dlg.exec():
            new_name = dlg.get_name()
            if new_name and new_name != self.camera.name:
                self.camera.name = new_name
                self.update_camera_info()
                self.camera_updated.emit(self.camera.id)

    def contextMenuEvent(self, event):
        """Menu de contexto com botão direito do mouse."""
        menu = QMenu(self)

        act_rename = QAction("✏️ Renomear Câmera...", self)
        act_rename.triggered.connect(self._rename_camera)
        menu.addAction(act_rename)

        act_max = QAction("↙ Restaurar Grade" if self._is_maximized_in_grid else "↗ Maximizar Câmera", self)
        act_max.triggered.connect(self._on_maximize_clicked)
        menu.addAction(act_max)

        act_recon = QAction("🔄 Reconectar", self)
        act_recon.triggered.connect(self._restart_stream)
        menu.addAction(act_recon)

        act_snap = QAction("📸 Tirar Foto", self)
        act_snap.triggered.connect(self._take_snapshot)
        menu.addAction(act_snap)

        menu.addSeparator()

        # Opções de PTZ e Alarme
        has_ptz = (self.camera.camera_type == "icsee" or bool(self.camera.onvif_port))
        if has_ptz:
            act_ptz = QAction("🎮 Controle PTZ (Mover)", self)
            act_ptz.triggered.connect(self._toggle_ptz)
            menu.addAction(act_ptz)

        if self.camera.camera_type == "icsee":
            act_alarm = QAction("🚨 Configurações de Alarme & IA...", self)
            act_alarm.triggered.connect(self._open_alarm_dialog)
            menu.addAction(act_alarm)

            menu.addSeparator()
        else:
            act_detect = QAction("🔍 Detectar Recursos iCSee", self)
            act_detect.triggered.connect(self._detect_and_activate_icsee)
            menu.addAction(act_detect)

            menu.addSeparator()

        act_edit = QAction("⚙️ Editar Configurações", self)
        act_edit.triggered.connect(lambda: self.edit_requested.emit(self.camera.id))
        menu.addAction(act_edit)

        act_del = QAction("🗑️ Remover Câmera", self)
        act_del.triggered.connect(lambda: self.remove_requested.emit(self.camera.id))
        menu.addAction(act_del)

        menu.exec(event.globalPos())
