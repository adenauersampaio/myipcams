from typing import Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QLabel,
    QMessageBox,
)

from ..core.camera import Camera
from ..network.xm_client import XMClient
from .assets import get_app_icon


class AlarmLoaderThread(QThread):
    loaded = pyqtSignal(bool, dict)

    def __init__(self, camera: Camera):
        super().__init__()
        self.camera = camera

    def run(self):
        client = XMClient(
            ip=self.camera.current_ip,
            port=self.camera.xm_port,
            username=self.camera.username,
            password=self.camera.password,
            timeout=3.5,
        )
        try:
            if not client.login():
                self.loaded.emit(False, {})
                return
            config = client.get_alarm_config()
            client.disconnect()
            self.loaded.emit(True, config)
        except Exception:
            client.disconnect()
            self.loaded.emit(False, {})


class AlarmSaverThread(QThread):
    saved = pyqtSignal(bool, str)

    def __init__(self, camera: Camera, motion_enable: bool, motion_level: int, human_enable: bool):
        super().__init__()
        self.camera = camera
        self.motion_enable = motion_enable
        self.motion_level = motion_level
        self.human_enable = human_enable

    def run(self):
        client = XMClient(
            ip=self.camera.current_ip,
            port=self.camera.xm_port,
            username=self.camera.username,
            password=self.camera.password,
            timeout=4.0,
        )
        try:
            if not client.login():
                self.saved.emit(False, "Falha na autenticação com a câmera.")
                return

            ok_m = client.set_motion_detection(self.motion_enable, self.motion_level)
            ok_h = client.set_human_detection(self.human_enable)
            client.disconnect()

            if ok_m and ok_h:
                self.saved.emit(True, "Configurações de alarme salvas com sucesso!")
            elif ok_m or ok_h:
                self.saved.emit(True, "Configurações salvas parcialmente.")
            else:
                self.saved.emit(False, "Câmera recusou a alteração dos parâmetros de alarme.")
        except Exception as e:
            client.disconnect()
            self.saved.emit(False, f"Erro ao comunicar com a câmera: {e}")


class XMAlarmDialog(QDialog):
    """Diálogo modal para gerenciar alarmes de presença e IA em câmeras iCSee/Xiongmai."""

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.setWindowTitle(f"Alarmes e IA - {camera.name}")
        self.setWindowIcon(get_app_icon())
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Grupo Detecção de Movimento Padrão
        group_motion = QGroupBox("Detecção de Movimento (Padrão)")
        form_motion = QFormLayout(group_motion)

        self.chk_motion = QCheckBox("Habilitar Detecção de Movimento")
        self.combo_level = QComboBox()
        self.combo_level.addItems([
            "1 - Muito Baixa",
            "2 - Baixa",
            "3 - Média",
            "4 - Alta",
            "5 - Muito Alta",
            "6 - Máxima"
        ])
        self.combo_level.setCurrentIndex(2)  # Média = nível 3

        form_motion.addRow("", self.chk_motion)
        form_motion.addRow("Sensibilidade:", self.combo_level)
        layout.addWidget(group_motion)

        # 2. Grupo Detecção Humana (Humanoid / IA)
        group_human = QGroupBox("Detecção Humana (IA / Presença)")
        form_human = QFormLayout(group_human)

        self.chk_human = QCheckBox("Habilitar Detecção de Silhueta Humana")
        lbl_info = QLabel("Filtra alarmes falsos causados por animais, árvores ou insetos.")
        lbl_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_info.setWordWrap(True)

        form_human.addRow("", self.chk_human)
        form_human.addRow("", lbl_info)
        layout.addWidget(group_human)

        # 3. Status label
        self.lbl_status = QLabel("Consultando câmera...")
        self.lbl_status.setStyleSheet("color: #60A5FA; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # 4. Botões de ação
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Fechar")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Salvar Configurações")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_settings)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _load_current_settings(self):
        self.lbl_status.setText("Carregando configurações atuais da câmera...")
        self.loader_thread = AlarmLoaderThread(self.camera)
        self.loader_thread.loaded.connect(self._on_settings_loaded)
        self.loader_thread.start()

    def _on_settings_loaded(self, success: bool, config: dict):
        self.btn_save.setEnabled(True)
        if not success:
            self.lbl_status.setText("Não foi possível ler as configurações (verifique senha ou conexão).")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")
            return

        self.lbl_status.setText("Configurações carregadas da câmera.")
        self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")

        # Aplica valores de movimento
        motion_list = config.get("motion", [])
        if motion_list and isinstance(motion_list, list):
            m = motion_list[0]
            self.chk_motion.setChecked(bool(m.get("Enable", False)))
            lvl = int(m.get("Level", 3))
            self.combo_level.setCurrentIndex(max(0, min(5, lvl - 1)))

        # Aplica valores de detecção humana
        human_list = config.get("human", [])
        if human_list and isinstance(human_list, list):
            h = human_list[0]
            self.chk_human.setChecked(bool(h.get("Enable", False)))

    def _save_settings(self):
        self.btn_save.setEnabled(False)
        self.lbl_status.setText("Salvando novas configurações na câmera...")
        self.lbl_status.setStyleSheet("color: #60A5FA; font-size: 11px;")

        level = self.combo_level.currentIndex() + 1
        self.saver_thread = AlarmSaverThread(
            camera=self.camera,
            motion_enable=self.chk_motion.isChecked(),
            motion_level=level,
            human_enable=self.chk_human.isChecked(),
        )
        self.saver_thread.saved.connect(self._on_settings_saved)
        self.saver_thread.start()

    def _on_settings_saved(self, success: bool, message: str):
        self.btn_save.setEnabled(True)
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Erro ao Salvar", message)
            self.lbl_status.setText(message)
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")
