import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QMessageBox
from myipcams.core.camera import Camera
from myipcams.network.onvif_ptz import ONVIFPTZClient
from myipcams.ui.camera_widget import CameraWidget

app = QApplication.instance() or QApplication([])


class TestReboot(unittest.TestCase):
    @patch("requests.post")
    def test_onvif_reboot_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """<?xml version="1.0" encoding="utf-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
    <SOAP-ENV:Body>
        <tds:SystemRebootResponse>
            <tds:Message>Rebooting in 60 seconds</tds:Message>
        </tds:SystemRebootResponse>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""
        mock_post.return_value = mock_resp

        client = ONVIFPTZClient(ip="192.168.1.100", port=80, username="admin", password="password")
        result = client.reboot()

        self.assertTrue(result)
        self.assertTrue(mock_post.called)
        sent_body = mock_post.call_args[1]["data"].decode("utf-8")
        self.assertIn("SystemReboot", sent_body)
        self.assertIn("http://www.onvif.org/ver10/device/wsdl", sent_body)

    @patch("requests.post")
    def test_onvif_reboot_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        client = ONVIFPTZClient(ip="192.168.1.100", port=80, username="admin", password="password")
        result = client.reboot()

        self.assertFalse(result)

    def test_camera_widget_has_reboot_ui(self):
        cam = Camera(name="Cam Teste", current_ip="192.168.1.50", enabled=False)
        widget = CameraWidget(cam)

        # Verifica se o botão de reboot existe no footer
        self.assertIsNotNone(widget.btn_reboot)
        self.assertEqual(widget.btn_reboot.text(), "⚡")
        self.assertIn("Reiniciar Câmera", widget.btn_reboot.toolTip())

        widget.stop_stream()

    @patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No)
    def test_confirm_and_reboot_cancelled(self, mock_question):
        cam = Camera(name="Cam Cancelada", current_ip="192.168.1.50", enabled=False)
        widget = CameraWidget(cam)

        with patch.object(widget, "reboot_finished") as mock_signal:
            widget._confirm_and_reboot()
            mock_question.assert_called_once()
            # Como foi cancelado, nada deve ser emitido
            mock_signal.emit.assert_not_called()

        widget.stop_stream()


if __name__ == "__main__":
    unittest.main()
