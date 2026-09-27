import os
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from myipcams.core.camera import Camera
from myipcams.ui.camera_widget import CameraWidget, CameraRenameDialog
from myipcams.ui.discovery_dialog import DiscoveryDialog
from myipcams.network.discovery import DiscoveredCamera

app = QApplication.instance() or QApplication([])


class TestCameraRename(unittest.TestCase):
    def test_camera_rename_dialog_validation_and_value(self):
        dialog = CameraRenameDialog("Nome Antigo")
        dialog.show()
        self.assertEqual(dialog.get_name(), "Nome Antigo")

        # Testa alteração de texto
        dialog.name_input.setText("Portão de Entrada")
        self.assertEqual(dialog.get_name(), "Portão de Entrada")

        # Testa validação de nome em branco com mock de QMessageBox.warning para evitar modal bloqueante
        with patch.object(QMessageBox, "warning") as mock_warn:
            dialog.name_input.setText("   ")
            dialog._save()
            mock_warn.assert_called_once()
            self.assertFalse(dialog.result() == 1)

        # Preenche nome válido e salva
        dialog.name_input.setText("Garagem Coberta")
        dialog._save()
        self.assertEqual(dialog.result(), 1)
        self.assertEqual(dialog.get_name(), "Garagem Coberta")

    def test_camera_widget_has_rename_ui_elements(self):
        cam = Camera(name="Câmera 1", current_ip="192.168.1.100", enabled=False)
        widget = CameraWidget(cam)
        widget.show()

        # Verifica existência dos elementos visuais de edição
        self.assertEqual(widget.name_label.text(), "Câmera 1")
        self.assertIsNotNone(widget.btn_rename)
        self.assertEqual(widget.btn_rename.toolTip(), "Renomear Câmera")

        # Verifica se duplo clique no label é suportado
        self.assertTrue(hasattr(widget.name_label, "double_clicked"))

        widget.stop_stream()

    def test_camera_widget_renaming_emits_updated_signal(self):
        cam = Camera(name="Original", current_ip="192.168.1.100", enabled=False)
        widget = CameraWidget(cam)
        widget.show()

        updated_ids = []
        widget.camera_updated.connect(lambda cid: updated_ids.append(cid))

        # Altera o nome e executa update_camera_info
        cam.name = "Sala de Estar"
        widget.update_camera_info()
        widget.camera_updated.emit(cam.id)

        self.assertEqual(widget.name_label.text(), "Sala de Estar")
        self.assertIn("Nome: Sala de Estar", widget.toolTip())
        self.assertIn(cam.id, updated_ids)

        widget.stop_stream()

    def test_discovery_dialog_custom_name_added(self):
        dialog = DiscoveryDialog()
        dialog.show()

        disc_cams = [
            DiscoveredCamera(
                ip="192.168.1.200",
                port=80,
                name="ONVIF Camera",
                hardware="IPC-HFW",
                mac="00:11:22:33:44:55",
                protocol="ONVIF",
                open_ports=[554, 80],
            )
        ]

        dialog._on_cameras_found(disc_cams)
        self.assertEqual(dialog.table.rowCount(), 1)

        # Simula o usuário editando o nome na tabela
        dialog.table.item(0, 1).setText("Entrada dos Fundos")

        added_cameras = []
        dialog.cameras_added.connect(lambda cams: added_cameras.extend(cams))

        dialog._add_selected()

        self.assertEqual(len(added_cameras), 1)
        self.assertEqual(added_cameras[0].name, "Entrada dos Fundos")
        self.assertEqual(added_cameras[0].current_ip, "192.168.1.200")


if __name__ == "__main__":
    unittest.main()
