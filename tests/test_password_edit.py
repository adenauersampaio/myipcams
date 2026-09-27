import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QLineEdit
from PyQt6.QtCore import Qt
from myipcams.ui.assets import get_eye_icon
from myipcams.ui.password_edit import PasswordLineEdit
from myipcams.ui.camera_edit_dialog import CameraEditDialog
from myipcams.ui.discovery_dialog import DiscoveryDialog
from myipcams.core.camera import Camera

app = QApplication.instance() or QApplication([])


class TestPasswordEdit(unittest.TestCase):
    def test_eye_icons_valid(self):
        icon_show = get_eye_icon(visible=False)
        icon_hide = get_eye_icon(visible=True)

        self.assertFalse(icon_show.isNull())
        self.assertFalse(icon_hide.isNull())

        for size in [16, 20, 24, 32]:
            pm_normal = icon_show.pixmap(size, size)
            self.assertFalse(pm_normal.isNull())
            self.assertEqual(pm_normal.width(), size)
            self.assertEqual(pm_normal.height(), size)

    def test_password_line_edit_initial_state(self):
        widget = PasswordLineEdit(placeholder="Digite a senha")
        self.assertEqual(widget.placeholderText(), "Digite a senha")
        self.assertEqual(widget.echoMode(), QLineEdit.EchoMode.Password)
        self.assertFalse(widget.is_password_visible())
        self.assertEqual(widget._toggle_action.toolTip(), "Mostrar senha")

    def test_password_line_edit_toggle(self):
        widget = PasswordLineEdit()
        widget.setText("super_secret_123")

        # Alterna para visível via ação
        widget._toggle_action.trigger()
        self.assertEqual(widget.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertTrue(widget.is_password_visible())
        self.assertEqual(widget._toggle_action.toolTip(), "Ocultar senha")
        self.assertEqual(widget.text(), "super_secret_123")

        # Alterna de volta para oculto via método
        widget.toggle_password_visibility()
        self.assertEqual(widget.echoMode(), QLineEdit.EchoMode.Password)
        self.assertFalse(widget.is_password_visible())
        self.assertEqual(widget._toggle_action.toolTip(), "Mostrar senha")
        self.assertEqual(widget.text(), "super_secret_123")

    def test_password_line_edit_cursor_preservation(self):
        widget = PasswordLineEdit()
        widget.setText("12345678")
        widget.setCursorPosition(3)

        widget.toggle_password_visibility()
        self.assertEqual(widget.cursorPosition(), 3)

        widget.toggle_password_visibility()
        self.assertEqual(widget.cursorPosition(), 3)

    def test_camera_edit_dialog_has_password_line_edit(self):
        cam = Camera(name="TestCam", current_ip="192.168.1.100", password="minhasenha")
        dialog = CameraEditDialog(cam)
        self.assertIsInstance(dialog.pass_edit, PasswordLineEdit)
        self.assertEqual(dialog.pass_edit.text(), "minhasenha")
        self.assertEqual(dialog.pass_edit.echoMode(), QLineEdit.EchoMode.Password)

        # Alterna visibilidade
        dialog.pass_edit.toggle_password_visibility()
        self.assertEqual(dialog.pass_edit.echoMode(), QLineEdit.EchoMode.Normal)

    def test_discovery_dialog_has_password_line_edit(self):
        dialog = DiscoveryDialog()
        self.assertIsInstance(dialog.pass_input, PasswordLineEdit)
        self.assertEqual(dialog.pass_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dialog.pass_input.placeholderText(), "senha")

        dialog.pass_input.setText("default_pass")
        dialog.pass_input.toggle_password_visibility()
        self.assertEqual(dialog.pass_input.text(), "default_pass")
        self.assertEqual(dialog.pass_input.echoMode(), QLineEdit.EchoMode.Normal)


if __name__ == "__main__":
    unittest.main()
