import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from myipcams.core.camera import Camera
from myipcams.player.audio_player import CameraAudioPlayer
from myipcams.ui.camera_widget import CameraWidget

app = QApplication.instance() or QApplication([])


class TestCameraAudio(unittest.TestCase):
    def test_audio_player_initial_state(self):
        player = CameraAudioPlayer("rtsp://192.168.1.100:554/live/ch0")
        self.assertTrue(player.is_muted())
        self.assertFalse(player.is_playing())
        self.assertEqual(player.get_volume(), 80)

    def test_audio_player_volume_bounds(self):
        player = CameraAudioPlayer()
        volumes_recorded = []
        player.volume_changed.connect(lambda v: volumes_recorded.append(v))

        player.set_volume(50)
        self.assertEqual(player.get_volume(), 50)

        # Testa limites (clamps) 0 e 100
        player.set_volume(150)
        self.assertEqual(player.get_volume(), 100)

        player.set_volume(-20)
        self.assertEqual(player.get_volume(), 0)

        self.assertEqual(volumes_recorded, [50, 100, 0])

    def test_audio_player_toggle_mute(self):
        player = CameraAudioPlayer("rtsp://192.168.1.100:554/live/ch0")
        mute_states = []
        player.muted_changed.connect(lambda m: mute_states.append(m))

        # Inicia mutado -> toggle desmuta
        new_state = player.toggle_mute()
        self.assertFalse(new_state)
        self.assertFalse(player.is_muted())

        # Toggle muta de novo
        new_state = player.toggle_mute()
        self.assertTrue(new_state)
        self.assertTrue(player.is_muted())

        self.assertEqual(mute_states, [False, True])
        player.stop()

    def test_camera_widget_has_audio_ui(self):
        cam = Camera(name="Câmera Som", current_ip="192.168.1.150", enabled=False)
        widget = CameraWidget(cam)

        self.assertIsNotNone(widget.btn_audio)
        self.assertEqual(widget.btn_audio.text(), "🔇")
        self.assertIn("Ativar Som", widget.btn_audio.toolTip())
        self.assertTrue(widget.audio_player.is_muted())

        # Clica para ativar o som
        widget._toggle_audio()
        self.assertFalse(widget.audio_player.is_muted())
        self.assertEqual(widget.btn_audio.text(), "🔊")
        self.assertIn("Desativar Som", widget.btn_audio.toolTip())

        # Clica para desativar o som
        widget._toggle_audio()
        self.assertTrue(widget.audio_player.is_muted())
        self.assertEqual(widget.btn_audio.text(), "🔇")

        widget.stop_stream()


if __name__ == "__main__":
    unittest.main()
