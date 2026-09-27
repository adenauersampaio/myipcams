from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
    QLabel,
    QMessageBox,
    QComboBox,
    QWidget,
    QHBoxLayout,
    QApplication,
)

from ..core.camera import Camera
from ..core.storage import CameraStorage
from ..core.tracker import IPTracker
from .camera_grid import CameraGrid
from .camera_edit_dialog import CameraEditDialog
from .discovery_dialog import DiscoveryDialog
from .about_dialog import AboutDialog
from .assets import get_app_icon
from .styles import DARK_THEME_QSS


class Bridge(QObject):
    """Auxiliar para encaminhar sinais entre threads para a UI Qt."""
    ip_changed_signal = pyqtSignal(object, str, str)


class MainWindow(QMainWindow):
    """Janela principal do aplicativo MyIPCams."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("MyIPCams - Visualizador & Rastreamento Dinâmico de Câmeras IP")
        self.setWindowIcon(get_app_icon())
        self.setMinimumSize(480, 320)
        self.setStyleSheet(DARK_THEME_QSS)
        self._init_window_geometry()

        self.storage = CameraStorage(config_path)
        self.cameras: List[Camera] = self.storage.load_cameras()

        # Ponte de sinais para thread-safety
        self.bridge = Bridge()
        self.bridge.ip_changed_signal.connect(self._on_ip_changed_in_ui)

        # Inicia o IPTracker em segundo plano
        self.tracker = IPTracker(
            get_cameras_fn=lambda: self.cameras,
            on_ip_changed=self._on_tracker_ip_changed,
            check_interval=30.0,
        )

        self._setup_ui()
        self.tracker.start()

    def _init_window_geometry(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Ajusta tamanho para caber confortavelmente no espaço visível da tela
            w = min(1100, max(540, avail.width() - 30))
            h = min(720, max(380, avail.height() - 50))
            self.resize(w, h)
        else:
            self.resize(960, 540)

    def _setup_ui(self):
        # 1. Barra de Ferramentas
        toolbar = QToolBar("Barra Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_add = QAction("➕ Adicionar Câmera", self)
        act_add.setToolTip("Adicionar uma câmera manualmente pelo IP ou MAC")
        act_add.triggered.connect(self._add_camera_manual)
        toolbar.addAction(act_add)

        act_scan = QAction("🔍 Escanear Rede", self)
        act_scan.setToolTip("Buscar câmeras ONVIF na rede local automaticamente")
        act_scan.triggered.connect(self._open_discovery)
        toolbar.addAction(act_scan)

        toolbar.addSeparator()

        # Seletor de Mosaico / Layout
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setContentsMargins(4, 0, 4, 0)
        grid_layout.addWidget(QLabel("Layout:"))
        self.combo_layout = QComboBox()
        self.combo_layout.addItems(["Auto", "1x1", "2x2", "3x3"])
        self.combo_layout.currentTextChanged.connect(self._change_layout_mode)
        grid_layout.addWidget(self.combo_layout)
        toolbar.addWidget(grid_widget)

        toolbar.addSeparator()

        act_track = QAction("⚡ Rastrear IPs Agora", self)
        act_track.setToolTip("Verifica imediatamente se os IPs das câmeras mudaram na rede")
        act_track.triggered.connect(self._force_track_ips)
        toolbar.addAction(act_track)

        act_reconnect = QAction("🔄 Reconectar Todas", self)
        act_reconnect.setToolTip("Reinicia as conexões de todas as câmeras")
        act_reconnect.triggered.connect(self._reconnect_all)
        toolbar.addAction(act_reconnect)

        toolbar.addSeparator()

        act_about = QAction("ℹ️ Sobre", self)
        act_about.setIcon(get_app_icon())
        act_about.setToolTip("Sobre o MyIPCams")
        act_about.triggered.connect(self._open_about)
        toolbar.addAction(act_about)

        # 2. Área Central (Grade de Câmeras)
        self.grid = CameraGrid(self)
        self.grid.edit_camera_requested.connect(self._edit_camera_by_id)
        self.grid.remove_camera_requested.connect(self._remove_camera_by_id)
        self.grid.camera_updated.connect(lambda _: self.storage.save_cameras(self.cameras))
        self.grid.cameras_reordered.connect(self._on_cameras_reordered)
        self.grid.scan_network_requested.connect(self._open_discovery)
        self.grid.add_camera_requested.connect(self._add_camera_manual)
        self.setCentralWidget(self.grid)
        self.grid.set_cameras(self.cameras)

        # 3. Barra de Status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_cam_count = QLabel(f"Câmeras: {len(self.cameras)}")
        self.status_bar.addWidget(self.status_cam_count)

        self.status_tracker_msg = QLabel(" | Monitor de IP ativo (verificando ARP & ONVIF a cada 30s)")
        self.status_bar.addWidget(self.status_tracker_msg)

    def _change_layout_mode(self, mode_text: str):
        self.grid.set_layout_mode(mode_text.lower())

    def _add_camera_manual(self):
        dialog = CameraEditDialog(parent=self)
        if dialog.exec():
            new_cam = dialog.camera
            self.cameras.append(new_cam)
            self.storage.save_cameras(self.cameras)
            self.grid.set_cameras(self.cameras)
            self._update_status_counts()

    def _edit_camera_by_id(self, camera_id: str):
        cam = next((c for c in self.cameras if c.id == camera_id), None)
        if not cam:
            return
        dialog = CameraEditDialog(camera=cam, parent=self)
        if dialog.exec():
            self.storage.save_cameras(self.cameras)
            self.grid.set_cameras(self.cameras)

    def _remove_camera_by_id(self, camera_id: str):
        cam = next((c for c in self.cameras if c.id == camera_id), None)
        if not cam:
            return
        reply = QMessageBox.question(
            self,
            "Remover Câmera",
            f"Deseja realmente remover a câmera '{cam.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cameras = [c for c in self.cameras if c.id != camera_id]
            self.storage.save_cameras(self.cameras)
            self.grid.set_cameras(self.cameras)
            self._update_status_counts()

    def _open_discovery(self):
        dialog = DiscoveryDialog(parent=self)
        dialog.cameras_added.connect(self._on_discovered_cameras_added)
        dialog.exec()

    def _on_discovered_cameras_added(self, new_cameras: List[Camera]):
        added_count = 0
        for new_cam in new_cameras:
            # Verifica se já não existe câmera com o mesmo MAC ou UUID ou IP
            exists = False
            for existing in self.cameras:
                if new_cam.mac_address and existing.mac_address == new_cam.mac_address:
                    exists = True
                    break
                if new_cam.onvif_uuid and existing.onvif_uuid == new_cam.onvif_uuid:
                    exists = True
                    break
            if not exists:
                self.cameras.append(new_cam)
                added_count += 1

        if added_count > 0:
            self.storage.save_cameras(self.cameras)
            self.grid.set_cameras(self.cameras)
            self._update_status_counts()
            QMessageBox.information(
                self,
                "Câmeras Adicionadas",
                f"{added_count} nova(s) câmera(s) adicionada(s) com sucesso!"
            )
        else:
            QMessageBox.information(
                self,
                "Aviso",
                "As câmeras selecionadas já estavam cadastradas."
            )

    def _force_track_ips(self):
        self.status_bar.showMessage("Rastreando novos IPs de todas as câmeras na rede...", 3000)
        self.tracker.check_all_cameras()
        self.status_bar.showMessage("Varredura de IPs concluída!", 4000)

    def _reconnect_all(self):
        self.status_bar.showMessage("Reconectando todas as câmeras...", 3000)
        self.grid.set_cameras(self.cameras)

    def _on_tracker_ip_changed(self, camera: Camera, old_ip: str, new_ip: str):
        """Disparado pela thread de background do IPTracker."""
        self.bridge.ip_changed_signal.emit(camera, old_ip, new_ip)

    def _on_ip_changed_in_ui(self, camera: Camera, old_ip: str, new_ip: str):
        """Manipulado na thread principal do Qt."""
        self.storage.save_cameras(self.cameras)
        self.grid.update_camera_ip(camera.id, new_ip)
        msg = f"⚡ IP da Câmera '{camera.name}' atualizado dinamicamente: {old_ip} ➔ {new_ip}"
        self.status_bar.showMessage(msg, 10000)
        print(f"[MainWindow] {msg}")

    def _on_cameras_reordered(self, reordered_cameras: List[Camera]):
        """Persiste a nova ordem das câmeras após movimentação/arraste na grade."""
        self.cameras = list(reordered_cameras)
        self.storage.save_cameras(self.cameras)
        self.status_bar.showMessage("Ordem dos cards de câmeras atualizada e salva!", 3000)

    def _update_status_counts(self):
        self.status_cam_count.setText(f"Câmeras: {len(self.cameras)}")

    def _open_about(self):
        dialog = AboutDialog(parent=self)
        dialog.exec()

    def closeEvent(self, event):
        """Ao fechar o aplicativo, para os workers e o tracker."""
        self.tracker.stop()
        self.grid.stop_all()
        super().closeEvent(event)
