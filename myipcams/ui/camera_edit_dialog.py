from typing import Optional
import cv2
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QCheckBox,
    QLabel,
    QMessageBox,
    QGroupBox,
)
from ..core.camera import Camera
from ..network.arp import ARPTable, normalize_mac
from ..network.xm_client import probe_device
from .assets import get_app_icon
from .password_edit import PasswordLineEdit


class ConnectionTester(QThread):
    result_ready = pyqtSignal(bool, str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ret, _ = cap.read()
            cap.release()
            if ret:
                self.result_ready.emit(True, "Conexão RTSP bem-sucedida! Stream recebido.")
            else:
                self.result_ready.emit(False, "Falha ao ler frame RTSP. Verifique usuário, senha e caminho do canal.")
        except Exception as e:
            self.result_ready.emit(False, f"Erro ao conectar: {e}")


class CameraEditDialog(QDialog):
    """Diálogo modal para adicionar ou editar parâmetros de uma câmera."""

    reboot_result_ready = pyqtSignal(bool, str)

    def __init__(self, camera: Optional[Camera] = None, parent=None):
        super().__init__(parent)
        self.camera = camera or Camera()
        self.is_new = camera is None
        self.setWindowTitle("Configurar Câmera" if not self.is_new else "Adicionar Nova Câmera")
        self.setWindowIcon(get_app_icon())
        self.setMinimumWidth(450)

        self.reboot_result_ready.connect(self._on_reboot_result)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ex: Garagem, Entrada Principal")

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("Ex: 192.168.1.120")
        self.ip_edit.textChanged.connect(self._on_ip_changed)

        # Campo MAC com botão de busca automática
        mac_layout = QHBoxLayout()
        self.mac_edit = QLineEdit()
        self.mac_edit.setPlaceholderText("Ex: a4:12:42:3b:01:2c (necessário p/ rastreamento dinâmico)")
        self.btn_auto_mac = QPushButton("Detectar MAC")
        self.btn_auto_mac.setObjectName("secondaryBtn")
        self.btn_auto_mac.clicked.connect(self._detect_mac)
        mac_layout.addWidget(self.mac_edit)
        mac_layout.addWidget(self.btn_auto_mac)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(554)

        # Caminho RTSP com sugestões de fabricantes populares
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        common_paths = [
            "/live/ch0",                    # Câmeras genéricas / Yoosee
            "/h264Preview_01_main",         # Reolink
            "/cam/realmonitor?channel=1&subtype=0", # Dahua / Intelbras
            "/Streaming/Channels/101",      # Hikvision
            "/onvif1",                      # Câmeras ONVIF padrão
            "/stream1",                     # TP-Link Tapo
        ]
        self.path_combo.addItems(common_paths)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Usuário (ex: admin)")

        self.pass_edit = PasswordLineEdit(placeholder="Senha da câmera")

        self.enabled_check = QCheckBox("Câmera Habilitada")
        self.enabled_check.setChecked(True)

        form.addRow("Nome da Câmera:", self.name_edit)
        form.addRow("Endereço IP:", self.ip_edit)
        form.addRow("Endereço MAC:", mac_layout)
        form.addRow("Porta RTSP:", self.port_spin)
        form.addRow("Caminho do Stream:", self.path_combo)
        form.addRow("Usuário RTSP:", self.user_edit)
        form.addRow("Senha:", self.pass_edit)
        form.addRow("", self.enabled_check)

        layout.addLayout(form)

        # 2. Grupo de Recursos Especiais (iCSee / PTZ / Alarmes)
        group_features = QGroupBox("Recursos Especiais (iCSee / PTZ / Alarmes)")
        form_features = QFormLayout(group_features)
        form_features.setSpacing(8)

        type_row = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItem("Genérica (Apenas RTSP)", "generic")
        self.type_combo.addItem("iCSee / Xiongmai (PTZ e Alarmes)", "icsee")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        self.btn_auto_detect_xm = QPushButton("🔍 Detectar Recursos iCSee")
        self.btn_auto_detect_xm.setObjectName("secondaryBtn")
        self.btn_auto_detect_xm.setToolTip("Testa na rede se a câmera responde na porta 34567 (iCSee/Xiongmai)")
        self.btn_auto_detect_xm.clicked.connect(self._detect_xm_features)

        type_row.addWidget(self.type_combo, stretch=1)
        type_row.addWidget(self.btn_auto_detect_xm)

        self.xm_port_spin = QSpinBox()
        self.xm_port_spin.setRange(1, 65535)
        self.xm_port_spin.setValue(34567)
        self.xm_port_row_label = QLabel("Porta de Controle:")

        form_features.addRow("Tipo / Recursos:", type_row)
        form_features.addRow(self.xm_port_row_label, self.xm_port_spin)

        layout.addWidget(group_features)

        # Botão de teste de conexão e diagnóstico
        self.test_status_label = QLabel("")
        self.test_status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        
        btn_test = QPushButton("Testar Conexão RTSP")
        btn_test.setObjectName("secondaryBtn")
        btn_test.clicked.connect(self._test_connection)
        
        test_box = QHBoxLayout()
        test_box.addWidget(btn_test)

        if not self.is_new:
            btn_reboot = QPushButton("⚡ Reiniciar Câmera")
            btn_reboot.setObjectName("secondaryBtn")
            btn_reboot.setToolTip("Envia comando de reinicialização remota para a câmera")
            btn_reboot.clicked.connect(self._reboot_camera)
            test_box.addWidget(btn_reboot)

        test_box.addWidget(self.test_status_label, stretch=1)
        layout.addLayout(test_box)

        # Botões de Salvar / Cancelar
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Salvar")
        btn_save.clicked.connect(self._save_and_accept)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _load_values(self):
        self.name_edit.setText(self.camera.name)
        self.ip_edit.setText(self.camera.current_ip)
        self.mac_edit.setText(self.camera.mac_address or "")
        self.port_spin.setValue(self.camera.rtsp_port)
        self.path_combo.setCurrentText(self.camera.rtsp_path)
        self.user_edit.setText(self.camera.username)
        self.pass_edit.setText(self.camera.password)
        self.enabled_check.setChecked(self.camera.enabled)

        # Carrega o tipo de câmera e porta Xiongmai
        idx = self.type_combo.findData(self.camera.camera_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        else:
            self.type_combo.setCurrentIndex(0)
        self.xm_port_spin.setValue(self.camera.xm_port)
        self._on_type_changed()

    def _on_type_changed(self):
        is_icsee = (self.type_combo.currentData() == "icsee")
        self.xm_port_row_label.setVisible(is_icsee)
        self.xm_port_spin.setVisible(is_icsee)

    def _detect_xm_features(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "Aviso", "Preencha primeiro o endereço IP da câmera.")
            return

        self.test_status_label.setText("Testando porta 34567 (iCSee)...")
        if probe_device(ip, port=34567, timeout=1.5):
            idx = self.type_combo.findData("icsee")
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.test_status_label.setText("✅ Dispositivo iCSee/Xiongmai detectado!")
            self.test_status_label.setStyleSheet("color: #34D399; font-size: 11px;")
            QMessageBox.information(
                self,
                "Recursos iCSee Detectados",
                f"A câmera em {ip} respondeu com sucesso ao protocolo Xiongmai/iCSee!\n\n"
                "O modo 'iCSee / Xiongmai' foi ativado para habilitar controle PTZ e alarmes."
            )
        else:
            self.test_status_label.setText("ℹ️ Dispositivo não respondeu ao protocolo iCSee.")
            self.test_status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
            QMessageBox.information(
                self,
                "Não Detectado",
                f"A câmera em {ip} não respondeu na porta 34567.\n\n"
                "Ela funcionará perfeitamente no modo padrão 'Genérica (Apenas RTSP)'."
            )

    def _on_ip_changed(self, text: str):
        if not self.mac_edit.text():
            mac = ARPTable.find_mac_by_ip(text)
            if mac:
                self.mac_edit.setText(mac)

    def _detect_mac(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "Aviso", "Preencha primeiro o endereço IP.")
            return
        
        # Dispara ping rápido para acordar a entrada ARP se necessário
        ARPTable.trigger_arp_refresh(ip)
        mac = ARPTable.find_mac_by_ip(ip)
        if mac:
            self.mac_edit.setText(mac)
            QMessageBox.information(self, "Sucesso", f"Endereço MAC detectado: {mac}")
        else:
            QMessageBox.warning(
                self,
                "Não Encontrado",
                "Endereço MAC ainda não consta na tabela ARP do sistema.\n"
                "Certifique-se de que a câmera está ligada e responda a pings na mesma rede local."
            )

    def _test_connection(self):
        self.test_status_label.setText("Testando conexão...")
        # Cria uma câmera temporária para gerar a URL
        temp_cam = Camera(
            current_ip=self.ip_edit.text().strip(),
            rtsp_port=self.port_spin.value(),
            rtsp_path=self.path_combo.currentText().strip(),
            username=self.user_edit.text().strip(),
            password=self.pass_edit.text().strip()
        )
        url = temp_cam.get_rtsp_url()

        self.tester = ConnectionTester(url)
        self.tester.result_ready.connect(self._on_test_result)
        self.tester.start()

    def _on_test_result(self, success: bool, message: str):
        if success:
            self.test_status_label.setText("✅ " + message)
            self.test_status_label.setStyleSheet("color: #34D399; font-size: 11px;")
        else:
            self.test_status_label.setText("❌ " + message)
            self.test_status_label.setStyleSheet("color: #F87171; font-size: 11px;")

    def _reboot_camera(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "Aviso", "Preencha primeiro o endereço IP.")
            return

        reply = QMessageBox.question(
            self,
            "Reiniciar Câmera",
            f"Deseja realmente enviar comando de reinicialização para a câmera em {ip}?\n\n"
            "⚠️ O dispositivo levará de 1 a 2 minutos para reiniciar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.test_status_label.setText("Enviando comando de reinício...")
        self.test_status_label.setStyleSheet("color: #FBBF24; font-size: 11px;")

        cam_type = self.type_combo.currentData() or "generic"
        xm_port = self.xm_port_spin.value()
        user = self.user_edit.text().strip()
        pwd = self.pass_edit.text().strip()
        onvif_port = self.camera.onvif_port or 80

        import threading

        def _worker():
            success = False
            if cam_type == "icsee":
                try:
                    from ..network.xm_client import XMClient
                    client = XMClient(ip=ip, port=xm_port, username=user, password=pwd, timeout=2.5)
                    success = client.reboot()
                except Exception:
                    pass

            if not success:
                try:
                    from ..network.onvif_ptz import ONVIFPTZClient
                    onvif = ONVIFPTZClient(ip=ip, port=onvif_port, username=user, password=pwd, timeout=2.5)
                    success = onvif.reboot()
                except Exception:
                    pass

            if not success and cam_type != "icsee":
                try:
                    from ..network.xm_client import XMClient
                    client = XMClient(ip=ip, port=xm_port, username=user, password=pwd, timeout=2.5)
                    success = client.reboot()
                except Exception:
                    pass

            msg = "Comando de reinicialização aceito!" if success else "Falha ao enviar comando de reinicialização."
            self.reboot_result_ready.emit(success, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_reboot_result(self, success: bool, message: str):
        if success:
            self.test_status_label.setText("✅ " + message)
            self.test_status_label.setStyleSheet("color: #34D399; font-size: 11px;")
            QMessageBox.information(
                self,
                "Reinicialização Enviada",
                "Comando de reinicialização enviado com sucesso para o dispositivo.\n"
                "A câmera ficará offline temporariamente durante a reinicialização."
            )
        else:
            self.test_status_label.setText("❌ " + message)
            self.test_status_label.setStyleSheet("color: #F87171; font-size: 11px;")
            QMessageBox.warning(
                self,
                "Falha na Reinicialização",
                "Não foi possível reiniciar a câmera.\n\n"
                "Verifique o usuário, senha e se o dispositivo suporta comandos de reinício via ONVIF ou iCSee."
            )

    def _save_and_accept(self):
        name = self.name_edit.text().strip()
        ip = self.ip_edit.text().strip()
        if not name or not ip:
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor preencha pelo menos Nome e IP.")
            return

        self.camera.name = name
        self.camera.current_ip = ip
        raw_mac = self.mac_edit.text().strip()
        self.camera.mac_address = normalize_mac(raw_mac) if raw_mac else None
        self.camera.rtsp_port = self.port_spin.value()
        self.camera.rtsp_path = self.path_combo.currentText().strip()
        self.camera.username = self.user_edit.text().strip()
        self.camera.password = self.pass_edit.text().strip()
        self.camera.camera_type = self.type_combo.currentData() or "generic"
        self.camera.xm_port = self.xm_port_spin.value()
        self.camera.enabled = self.enabled_check.isChecked()

        self.accept()

