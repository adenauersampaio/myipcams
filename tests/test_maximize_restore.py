import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6 import sip

from myipcams.core.camera import Camera
from myipcams.core.storage import CameraStorage
from myipcams.core.tracker import IPTracker
from myipcams.network.discovery import DiscoveredCamera
from myipcams.ui.camera_grid import CameraGrid
from myipcams.ui.discovery_dialog import DiscoveryDialog
from myipcams.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])
app.setFont(QFont("DejaVu Sans", 10))


class TestMaximizeRestore(unittest.TestCase):

    def setUp(self):
        self.cams = [
            Camera(id=f"cam-{i}", name=f"Camera {i}", current_ip=f"192.168.1.10{i}", enabled=False)
            for i in range(5)
        ]
        self.grid = CameraGrid()
        self.grid.set_cameras(self.cams)

    def tearDown(self):
        self.grid.stop_all()

    def test_maximize_and_restore_single_camera(self):
        # Estado inicial: todas as 5 câmeras devem estar visíveis
        for cam in self.cams:
            widget = self.grid.widgets[cam.id]
            self.assertFalse(widget._is_maximized_in_grid)
            self.assertFalse(widget.isHidden())

        # Maximiza câmera cam-0
        self.grid._toggle_maximize("cam-0")
        self.assertEqual(self.grid.maximized_camera_id, "cam-0")

        # Verifica widget da câmera maximizada
        w0 = self.grid.widgets["cam-0"]
        self.assertTrue(w0._is_maximized_in_grid)
        self.assertFalse(w0.isHidden())
        self.assertEqual(w0.btn_maximize.text(), "↙")

        # Verifica que as outras câmeras estão ocultas
        for cam in self.cams[1:]:
            w = self.grid.widgets[cam.id]
            self.assertFalse(w._is_maximized_in_grid)
            self.assertTrue(w.isHidden())

        # Restaura a grade original
        self.grid._toggle_maximize("cam-0")
        self.assertIsNone(self.grid.maximized_camera_id)

        # Todas as câmeras devem voltar a ficar visíveis e sem estado maximizado
        for cam in self.cams:
            widget = self.grid.widgets[cam.id]
            self.assertFalse(widget._is_maximized_in_grid)
            self.assertFalse(widget.isHidden())
            self.assertEqual(widget.btn_maximize.text(), "↗")
            self.assertFalse(sip.isdeleted(widget))

        # Splitters não devem ter sido deletados
        self.assertIsNotNone(self.grid._main_splitter)
        self.assertFalse(sip.isdeleted(self.grid._main_splitter))
        for rs in self.grid._row_splitters:
            self.assertFalse(sip.isdeleted(rs))

    def test_maximize_camera_in_different_row(self):
        # Com 5 câmeras e layout auto (cols=3), cam-3 e cam-4 ficam na linha 2 (índice 1)
        self.grid._toggle_maximize("cam-4")
        self.assertEqual(self.grid.maximized_camera_id, "cam-4")

        w4 = self.grid.widgets["cam-4"]
        self.assertTrue(w4._is_maximized_in_grid)
        self.assertFalse(w4.isHidden())

        # Linha 0 deve estar oculta
        row_0 = self.grid._row_splitters[0]
        row_1 = self.grid._row_splitters[1]
        self.assertTrue(row_0.isHidden())
        self.assertFalse(row_1.isHidden())

        # Restaura
        self.grid._toggle_maximize("cam-4")
        self.assertIsNone(self.grid.maximized_camera_id)
        self.assertFalse(row_0.isHidden())
        self.assertFalse(row_1.isHidden())
        self.assertFalse(w4._is_maximized_in_grid)

    def test_repeated_maximize_and_restore_stability(self):
        # Testa ciclo repetido de maximizar e restaurar sem crash e sem leaks
        for _ in range(5):
            self.grid._toggle_maximize("cam-1")
            self.assertEqual(self.grid.maximized_camera_id, "cam-1")
            self.grid._toggle_maximize("cam-1")
            self.assertIsNone(self.grid.maximized_camera_id)

        for cam in self.cams:
            w = self.grid.widgets[cam.id]
            self.assertFalse(sip.isdeleted(w))
            self.assertFalse(w.isHidden())


class TestDiscoveryDialogClosing(unittest.TestCase):

    def test_discovery_dialog_accepts_and_provides_cameras(self):
        dialog = DiscoveryDialog()
        cam_disc = DiscoveredCamera(
            ip="192.168.1.88",
            port=80,
            protocol="ONVIF",
            name="Câmera Descoberta",
            hardware="TestModel",
            mac="aa:bb:cc:dd:ee:ff",
        )
        dialog._on_cameras_found([cam_disc])

        # Simula clique em "Adicionar Selecionadas"
        dialog._add_selected()

        # O diálogo deve ter sido aceito
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        selected = dialog.get_selected_cameras()
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].current_ip, "192.168.1.88")
        self.assertEqual(selected[0].name, "Câmera Descoberta (TestModel)")

    @patch.object(IPTracker, "start")
    @patch.object(QMessageBox, "information")
    def test_main_window_discovery_adds_cameras_and_shows_info(self, mock_info, mock_tracker_start):
        with tempfile.TemporaryDirectory() as tmp:
            win = MainWindow(config_path=str(Path(tmp) / "cameras.json"))

            new_cam = Camera(
                id="test-new-cam",
                name="Nova Câmera",
                current_ip="192.168.10.99",
                mac_address="11:22:33:44:55:66",
                enabled=False,
            )

            with patch.object(DiscoveryDialog, "exec", return_value=QDialog.DialogCode.Accepted):
                with patch.object(DiscoveryDialog, "get_selected_cameras", return_value=[new_cam]):
                    win._open_discovery()

            self.assertEqual(len(win.cameras), 1)
            mock_info.assert_called_once()
            self.assertIn("1 nova(s) câmera(s) adicionada(s)", mock_info.call_args[0][2])
            win.grid.stop_all()


if __name__ == "__main__":
    unittest.main()
