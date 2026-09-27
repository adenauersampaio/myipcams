import os
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from myipcams.core.camera import Camera
from myipcams.ui.camera_widget import CameraWidget
from myipcams.ui.camera_edit_dialog import CameraEditDialog

# Instância única da QApplication para testes offscreen
app = QApplication.instance() or QApplication([])


class TestUIIcseeSupport(unittest.TestCase):
    def test_generic_camera_widget_hides_ptz(self):
        cam = Camera(
            name="Câmera Genérica",
            current_ip="192.168.1.50",
            camera_type="generic",
            onvif_port=0,
            enabled=False,
        )
        widget = CameraWidget(cam)
        self.assertTrue(widget.btn_ptz.isHidden())
        self.assertTrue(widget.ptz_overlay.isHidden())
        widget.stop_stream()

    def test_icsee_camera_widget_shows_ptz(self):
        cam = Camera(
            name="Câmera iCSee",
            current_ip="192.168.1.60",
            camera_type="icsee",
            xm_port=34567,
            enabled=False,
        )
        widget = CameraWidget(cam)
        self.assertFalse(widget.btn_ptz.isHidden())
        self.assertTrue(widget.ptz_overlay.isHidden())

        # Clicar no botão PTZ deve alternar a visibilidade do overlay
        widget._toggle_ptz()
        self.assertFalse(widget.ptz_overlay.isHidden())
        widget._toggle_ptz()
        self.assertTrue(widget.ptz_overlay.isHidden())
        widget.stop_stream()

    def test_camera_edit_dialog_loads_and_toggles_type(self):
        cam_gen = Camera(name="Gen", current_ip="192.168.1.10", camera_type="generic")
        dialog_gen = CameraEditDialog(cam_gen)
        self.assertEqual(dialog_gen.type_combo.currentData(), "generic")
        self.assertTrue(dialog_gen.xm_port_spin.isHidden())

        cam_icsee = Camera(name="XM", current_ip="192.168.1.20", camera_type="icsee", xm_port=34567)
        dialog_icsee = CameraEditDialog(cam_icsee)
        self.assertEqual(dialog_icsee.type_combo.currentData(), "icsee")
        self.assertFalse(dialog_icsee.xm_port_spin.isHidden())


if __name__ == "__main__":
    unittest.main()
