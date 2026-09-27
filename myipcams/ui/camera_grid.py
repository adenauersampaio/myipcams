import os
import math
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QSize
from PyQt6.QtGui import QMovie
from PyQt6 import sip
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from ..core.camera import Camera
from .camera_widget import CameraWidget
from .assets import get_camera_animation_path


class EmptyStateWidget(QWidget):
    """Card moderno de boas-vindas com a animação da câmera de segurança."""

    scan_requested = pyqtSignal()
    add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("emptyCard")
        card.setStyleSheet("""
            QFrame#emptyCard {
                background-color: #161920;
                border: 1px solid #28303F;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(14)

        # Animação da câmera de segurança
        self.movie_label = QLabel()
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_label.setStyleSheet("border-radius: 8px; background-color: #0D0F14;")
        self.movie: Optional[QMovie] = None

        anim_path = get_camera_animation_path()
        if anim_path and os.path.exists(anim_path):
            self.movie = QMovie(anim_path)
            self.movie.setScaledSize(QSize(360, 202))
            self.movie_label.setMovie(self.movie)

        card_layout.addWidget(self.movie_label)

        # Título e Subtítulo
        title = QLabel("Bem-vindo ao MyIPCams")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        card_layout.addWidget(title)

        subtitle = QLabel("Nenhuma câmera cadastrada no momento.\nComece buscando na rede local ou adicione os dados da câmera manualmente.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.4;")
        card_layout.addWidget(subtitle)

        # Botões de Ação Rápida
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_scan = QPushButton("🔍 Escanear Rede")
        btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scan.setToolTip("Buscar câmeras ONVIF automaticamente")
        btn_scan.clicked.connect(self.scan_requested.emit)
        btn_layout.addWidget(btn_scan)

        btn_add = QPushButton("➕ Adicionar Câmera")
        btn_add.setObjectName("secondaryBtn")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setToolTip("Cadastrar câmera manualmente por IP ou MAC")
        btn_add.clicked.connect(self.add_requested.emit)
        btn_layout.addWidget(btn_add)

        card_layout.addLayout(btn_layout)
        layout.addWidget(card)

    def start_animation(self):
        if self.movie and self.movie.state() != QMovie.MovieState.Running:
            self.movie.start()

    def stop_animation(self):
        if self.movie and self.movie.state() == QMovie.MovieState.Running:
            self.movie.stop()


class CameraGrid(QWidget):
    """Grade flexível de exibição com redimensionamento livre de bordas via QSplitters."""

    edit_camera_requested = pyqtSignal(str)
    remove_camera_requested = pyqtSignal(str)
    camera_updated = pyqtSignal(str)
    cameras_reordered = pyqtSignal(list)
    scan_network_requested = pyqtSignal()
    add_camera_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cameras: List[Camera] = []
        self.layout_mode = "auto"   # "auto", "1x1", "2x2", "3x3"
        self.widgets: Dict[str, CameraWidget] = {}
        self.maximized_camera_id: Optional[str] = None
        self._main_splitter: Optional[QSplitter] = None
        self._row_splitters: List[QSplitter] = []
        self._saved_splitter_state: Optional[QByteArray] = None
        self._saved_row_states: Dict[QSplitter, QByteArray] = {}

        self.setAcceptDrops(True)

        self.container_layout = QVBoxLayout(self)
        self.container_layout.setContentsMargins(4, 4, 4, 4)
        self.container_layout.setSpacing(0)

        # Widget de estado vazio com animação
        self.empty_state = EmptyStateWidget(self)
        self.empty_state.scan_requested.connect(self.scan_network_requested.emit)
        self.empty_state.add_requested.connect(self.add_camera_requested.emit)
        self.container_layout.addWidget(self.empty_state)
        self.empty_state.start_animation()

    def set_cameras(self, cameras: List[Camera]):
        """Atualiza a lista de câmeras exibidas."""
        self.cameras = list(cameras)
        current_ids = set(c.id for c in cameras)

        # Remove widgets antigos que não existem mais
        for cam_id in list(self.widgets.keys()):
            if cam_id not in current_ids:
                widget = self.widgets.pop(cam_id)
                widget.stop_stream()
                widget.setParent(None)
                widget.deleteLater()

        # Cria ou atualiza os widgets
        for cam in cameras:
            if cam.id in self.widgets:
                self.widgets[cam.id].update_camera_info()
            else:
                widget = CameraWidget(cam, self)
                widget.double_clicked.connect(self._toggle_maximize)
                widget.edit_requested.connect(self.edit_camera_requested.emit)
                widget.remove_requested.connect(self.remove_camera_requested.emit)
                widget.camera_updated.connect(self.camera_updated.emit)
                widget.reorder_requested.connect(self.reorder_cameras)
                widget.move_action_requested.connect(self.move_camera_action)
                self.widgets[cam.id] = widget

        self.rebuild_layout()

    def reorder_cameras(self, source_id: str, target_id: str):
        """Move o card source_id para a posição do card target_id na grade."""
        if source_id == target_id:
            return

        source_idx = next((i for i, c in enumerate(self.cameras) if c.id == source_id), None)
        target_idx = next((i for i, c in enumerate(self.cameras) if c.id == target_id), None)

        if source_idx is None or target_idx is None:
            return

        cam = self.cameras.pop(source_idx)
        self.cameras.insert(target_idx, cam)
        self.rebuild_layout()
        self.cameras_reordered.emit(list(self.cameras))

    def move_camera_action(self, camera_id: str, action: str):
        """Aplica ação de movimentação rápida ("first", "prev", "next", "last")."""
        idx = next((i for i, c in enumerate(self.cameras) if c.id == camera_id), None)
        if idx is None:
            return

        n = len(self.cameras)
        if n <= 1:
            return

        if action == "first":
            target_idx = 0
        elif action == "prev":
            target_idx = max(0, idx - 1)
        elif action == "next":
            target_idx = min(n - 1, idx + 1)
        elif action == "last":
            target_idx = n - 1
        else:
            return

        if target_idx != idx:
            cam = self.cameras.pop(idx)
            self.cameras.insert(target_idx, cam)
            self.rebuild_layout()
            self.cameras_reordered.emit(list(self.cameras))

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-myipcams-camera-id"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-myipcams-camera-id"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-myipcams-camera-id"):
            source_id = event.mimeData().data("application/x-myipcams-camera-id").data().decode("utf-8")
            if source_id and self.cameras:
                event.acceptProposedAction()
                self.move_camera_action(source_id, "last")
                return
        event.ignore()

    def update_camera_ip(self, camera_id: str, new_ip: str):
        """Notifica o widget correspondente sobre novo IP."""
        if camera_id in self.widgets:
            self.widgets[camera_id].on_ip_updated(new_ip)

    def set_layout_mode(self, mode: str):
        """Altera a disposição das câmeras (1x1, 2x2, 3x3, auto)."""
        self.layout_mode = mode.lower()
        self.rebuild_layout()

    def rebuild_layout(self):
        """Reconstrói a grade de QSplitters ao alterar layout, adicionar/remover ou reordenar câmeras."""
        self.maximized_camera_id = None

        # 1. Salva o estado dos splitters anteriores se existiam
        if self._main_splitter and not sip.isdeleted(self._main_splitter):
            try:
                self._saved_splitter_state = self._main_splitter.saveState()
            except Exception:
                pass

        # 2. Desacopla e reparenta com segurança todos os widgets existentes de câmeras para self
        # evitando que sejam destruídos quando os splitters antigos forem descartados
        for w in self.widgets.values():
            if not sip.isdeleted(w):
                w.setParent(self)
                w.hide()
                if hasattr(w, "set_maximized_state"):
                    w.set_maximized_state(False)

        # 3. Descarta splitters anteriores do container_layout
        if self._main_splitter:
            if not sip.isdeleted(self._main_splitter):
                self.container_layout.removeWidget(self._main_splitter)
                self._main_splitter.setParent(None)
                self._main_splitter.deleteLater()
            self._main_splitter = None
            self._row_splitters.clear()
            self._saved_row_states.clear()

        # 4. Caso vazio: Nenhuma câmera
        if not self.widgets:
            self.empty_state.show()
            self.empty_state.start_animation()
            if self.container_layout.indexOf(self.empty_state) == -1:
                self.container_layout.addWidget(self.empty_state)
            return
        else:
            self.empty_state.stop_animation()
            self.empty_state.hide()
            if self.container_layout.indexOf(self.empty_state) != -1:
                self.container_layout.removeWidget(self.empty_state)

        # 5. Constrói nova estrutura de splitters
        cam_list = [self.widgets[c.id] for c in self.cameras if c.id in self.widgets]
        if not cam_list:
            cam_list = list(self.widgets.values())
        cam_count = len(cam_list)

        # Determina colunas
        if self.layout_mode == "1x1":
            cols = 1
        elif self.layout_mode == "2x2":
            cols = 2
        elif self.layout_mode == "3x3":
            cols = 3
        else:
            if cam_count <= 1:
                cols = 1
            elif cam_count == 2:
                cols = 2
            elif cam_count <= 4:
                cols = 2
            elif cam_count <= 6:
                cols = 3
            elif cam_count <= 9:
                cols = 3
            else:
                cols = 4

        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setHandleWidth(6)
        self._main_splitter.setChildrenCollapsible(False)
        self._row_splitters = []
        self._saved_row_states = {}

        num_rows = math.ceil(cam_count / cols)
        for r in range(num_rows):
            row_widgets = cam_list[r * cols : (r + 1) * cols]
            row_splitter = QSplitter(Qt.Orientation.Horizontal)
            row_splitter.setHandleWidth(6)
            row_splitter.setChildrenCollapsible(False)
            self._row_splitters.append(row_splitter)

            for w in row_widgets:
                row_splitter.addWidget(w)
                w.show()

            row_splitter.setSizes([1000] * len(row_widgets))
            self._main_splitter.addWidget(row_splitter)

        self._main_splitter.setSizes([1000] * num_rows)

        if self._saved_splitter_state:
            try:
                self._main_splitter.restoreState(self._saved_splitter_state)
            except Exception:
                pass

        self.container_layout.addWidget(self._main_splitter)

    def _toggle_maximize(self, camera_id: str):
        """Alterna maximização de um card individual sem destruir ou recriar splitters."""
        if camera_id not in self.widgets:
            return

        if self.maximized_camera_id == camera_id:
            # Restaurar para grade normal
            self.maximized_camera_id = None
            if self._main_splitter and not sip.isdeleted(self._main_splitter):
                for row_splitter in self._row_splitters:
                    if not sip.isdeleted(row_splitter):
                        row_splitter.show()
                        for i in range(row_splitter.count()):
                            w = row_splitter.widget(i)
                            if w and not sip.isdeleted(w):
                                if hasattr(w, "set_maximized_state"):
                                    w.set_maximized_state(False)
                                w.show()

                if self._saved_splitter_state:
                    try:
                        self._main_splitter.restoreState(self._saved_splitter_state)
                    except Exception:
                        pass
                for row_splitter, state in self._saved_row_states.items():
                    if not sip.isdeleted(row_splitter):
                        try:
                            row_splitter.restoreState(state)
                        except Exception:
                            pass
        else:
            # Maximizar câmera selecionada
            self.maximized_camera_id = camera_id
            target_widget = self.widgets[camera_id]

            if self._main_splitter and not sip.isdeleted(self._main_splitter):
                try:
                    self._saved_splitter_state = self._main_splitter.saveState()
                except Exception:
                    pass

                self._saved_row_states.clear()
                for row_splitter in self._row_splitters:
                    if not sip.isdeleted(row_splitter):
                        try:
                            self._saved_row_states[row_splitter] = row_splitter.saveState()
                        except Exception:
                            pass

                        row_widgets = [row_splitter.widget(i) for i in range(row_splitter.count())]
                        if target_widget in row_widgets:
                            row_splitter.show()
                            for w in row_widgets:
                                if w and not sip.isdeleted(w):
                                    if w == target_widget:
                                        if hasattr(w, "set_maximized_state"):
                                            w.set_maximized_state(True)
                                        w.show()
                                    else:
                                        if hasattr(w, "set_maximized_state"):
                                            w.set_maximized_state(False)
                                        w.hide()
                        else:
                            row_splitter.hide()
                            for w in row_widgets:
                                if w and not sip.isdeleted(w):
                                    if hasattr(w, "set_maximized_state"):
                                        w.set_maximized_state(False)
                                    w.hide()

    def stop_all(self):
        """Para todos os streams ao fechar a janela."""
        for widget in self.widgets.values():
            widget.stop_stream()
        if hasattr(self, "empty_state"):
            self.empty_state.stop_animation()
