from typing import List
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QLineEdit,
    QComboBox,
    QMessageBox,
)
from ..core.camera import Camera
from ..network.discovery import NetworkDiscovery, DiscoveredCamera
from .assets import get_app_icon
from .password_edit import PasswordLineEdit


class DiscoveryWorker(QThread):
    cameras_found = pyqtSignal(list)
    progress_updated = pyqtSignal(int, int)
    finished_scan = pyqtSignal()

    def __init__(self, subnet: str, mode: str = "full"):
        super().__init__()
        self.subnet = subnet
        self.mode = mode

    def run(self):
        is_full = (self.mode == "full")

        def on_progress(completed, total):
            self.progress_updated.emit(completed, total)

        cams = NetworkDiscovery.discover_all(
            subnet_str=self.subnet,
            run_subnet_scan=is_full,
            progress_callback=on_progress if is_full else None,
        )
        self.cameras_found.emit(cams)
        self.finished_scan.emit()


class DiscoveryDialog(QDialog):
    """Diálogo que busca câmeras na rede local via Varredura Completa (Portas RTSP + ONVIF) ou Busca Rápida."""

    cameras_added = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Descobrir Câmeras na Rede Local")
        self.setWindowIcon(get_app_icon())
        self.setMinimumSize(780, 520)
        self.discovered_list: List[DiscoveredCamera] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Cabeçalho explicativo
        desc_label = QLabel(
            "Selecione o modo de varredura. A Varredura Completa testa em paralelo portas de vídeo (RTSP 554, HTTP 80/8080,\n"
            "portas de fabricantes) e ONVIF na sua sub-rede, encontrando inclusive câmeras que não respondem ao multicast."
        )
        desc_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc_label)

        # Configurações de Varredura (Modo e Sub-rede)
        config_bar = QHBoxLayout()
        config_bar.addWidget(QLabel("Modo de busca:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Varredura Completa (Portas RTSP + ONVIF)", "full")
        self.mode_combo.addItem("Varredura Rápida (Apenas Multicast ONVIF)", "fast")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        config_bar.addWidget(self.mode_combo)

        config_bar.addSpacing(15)
        config_bar.addWidget(QLabel("Sub-rede:"))
        self.subnet_input = QLineEdit()
        self.subnet_input.setText(NetworkDiscovery.get_primary_subnet())
        self.subnet_input.setPlaceholderText("192.168.1.0/24")
        self.subnet_input.setToolTip("Sub-rede IPv4 local no formato CIDR (ex: 192.168.1.0/24)")
        self.subnet_input.setMaximumWidth(150)
        config_bar.addWidget(self.subnet_input)
        config_bar.addStretch()

        layout.addLayout(config_bar)

        # Barra de Ação de Varredura
        scan_bar = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 Iniciar Varredura de Rede")
        self.btn_scan.clicked.connect(self._start_scan)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()

        scan_bar.addWidget(self.btn_scan)
        scan_bar.addWidget(self.progress_bar, stretch=1)
        layout.addLayout(scan_bar)

        # Tabela de Resultados
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "",
            "Nome / Identificação (editável)",
            "IP Atual",
            "Portas",
            "MAC Address",
            "Método",
            "UUID ONVIF",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        table_hint = QLabel("💡 Dica: Dê dois cliques na coluna 'Nome / Identificação' para personalizar o nome antes de adicionar.")
        table_hint.setStyleSheet("color: #60A5FA; font-size: 11px;")
        layout.addWidget(table_hint)

        # Credenciais padrão para aplicar nas câmeras adicionadas
        cred_layout = QHBoxLayout()
        cred_layout.addWidget(QLabel("Usuário padrão:"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("admin")
        self.user_input.setMaximumWidth(120)
        cred_layout.addWidget(self.user_input)

        cred_layout.addWidget(QLabel("Senha padrão:"))
        self.pass_input = PasswordLineEdit(placeholder="senha")
        self.pass_input.setMaximumWidth(140)
        cred_layout.addWidget(self.pass_input)

        cred_layout.addWidget(QLabel("Canal:"))
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        self.path_combo.addItems(["/live/ch0", "/onvif1", "/h264Preview_01_main", "/stream1"])
        cred_layout.addWidget(self.path_combo)

        layout.addLayout(cred_layout)

        # Barra inferior de botões
        footer = QHBoxLayout()
        self.status_label = QLabel("Pronto para escanear.")
        self.status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        footer.addWidget(self.status_label)
        footer.addStretch()

        btn_cancel = QPushButton("Fechar")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        self.btn_add = QPushButton("Adicionar Selecionadas")
        self.btn_add.clicked.connect(self._add_selected)

        footer.addWidget(btn_cancel)
        footer.addWidget(self.btn_add)
        layout.addLayout(footer)

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        self.subnet_input.setEnabled(mode == "full")

    def _start_scan(self):
        self.btn_scan.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.subnet_input.setEnabled(False)
        self.progress_bar.show()

        mode = self.mode_combo.currentData()
        subnet = self.subnet_input.text().strip() or NetworkDiscovery.get_primary_subnet()

        if mode == "full":
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText(f"Varrendo sub-rede {subnet} e dispositivos ONVIF...")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Varrendo a rede em busca de dispositivos ONVIF (multicast)...")

        self.table.setRowCount(0)
        self.discovered_list.clear()

        self.worker = DiscoveryWorker(subnet=subnet, mode=mode)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.cameras_found.connect(self._on_cameras_found)
        self.worker.finished_scan.connect(self._on_scan_finished)
        self.worker.start()

    def _on_progress_updated(self, completed: int, total: int):
        if total > 0:
            pct = int((completed / total) * 100)
            self.progress_bar.setValue(pct)
            self.status_label.setText(f"Varrendo sub-rede: {completed}/{total} IPs checados ({pct}%)...")

    def _on_cameras_found(self, cameras: List[DiscoveredCamera]):
        self.discovered_list = cameras
        self.table.setRowCount(len(cameras))

        for row, cam in enumerate(cameras):
            # Checkbox na primeira coluna
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, 0, chk_item)

            name_text = cam.name or "Câmera"
            if cam.hardware and cam.hardware not in name_text:
                name_text += f" ({cam.hardware})"
            name_item = QTableWidgetItem(name_text)
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
            name_item.setToolTip("Dê duplo clique para editar o nome da câmera antes de adicionar")
            self.table.setItem(row, 1, name_item)

            ip_item = QTableWidgetItem(cam.ip)
            ip_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 2, ip_item)

            ports_text = ", ".join(map(str, cam.open_ports)) if cam.open_ports else str(cam.port)
            ports_item = QTableWidgetItem(ports_text)
            ports_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 3, ports_item)

            mac_item = QTableWidgetItem(cam.mac or "Desconhecido")
            mac_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 4, mac_item)

            proto_item = QTableWidgetItem(cam.protocol)
            proto_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 5, proto_item)

            uuid_item = QTableWidgetItem(cam.uuid or "-")
            uuid_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 6, uuid_item)

    def _on_scan_finished(self):
        self.btn_scan.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self._on_mode_changed()
        self.progress_bar.hide()
        count = len(self.discovered_list)
        if count == 0:
            self.status_label.setText(
                "Nenhum dispositivo de vídeo encontrado. Verifique conexões e sub-rede."
            )
        else:
            self.status_label.setText(f"{count} dispositivo(s) encontrado(s) na rede.")

    def _add_selected(self):
        to_add: List[Camera] = []
        user = self.user_input.text().strip()
        passwd = self.pass_input.text().strip()
        path = self.path_combo.currentText().strip()

        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                if row < len(self.discovered_list):
                    disc = self.discovered_list[row]
                else:
                    continue

                name_item = self.table.item(row, 1)
                custom_name = name_item.text().strip() if name_item else ""
                camera_name = custom_name or disc.name or f"Câmera {disc.ip}"

                is_icsee = (34567 in disc.open_ports) or (disc.port == 34567) or ("xiongmai" in (disc.hardware or "").lower())
                cam = Camera(
                    name=camera_name,
                    current_ip=disc.ip,
                    mac_address=disc.mac,
                    onvif_uuid=disc.uuid,
                    vendor_model=disc.hardware,
                    username=user,
                    password=passwd,
                    rtsp_port=disc.rtsp_port if disc.rtsp_port else 554,
                    rtsp_path=path,
                    onvif_port=disc.port if disc.port else 80,
                    camera_type="icsee" if is_icsee else "generic",
                    xm_port=34567,
                )
                to_add.append(cam)

        if not to_add:
            QMessageBox.warning(self, "Aviso", "Nenhuma câmera marcada para adicionar.")
            return

        self._selected_cameras = to_add
        self.accept()
        self.cameras_added.emit(to_add)

    def get_selected_cameras(self) -> List[Camera]:
        """Retorna a lista de câmeras selecionadas pelo usuário antes do fechamento."""
        return getattr(self, "_selected_cameras", [])
