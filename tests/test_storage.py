import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from myipcams.core.camera import Camera
from myipcams.core.storage import CameraStorage, get_default_config_dir


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = str(Path(self.temp_dir.name) / "cameras.json")
        self.storage = CameraStorage(self.config_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load(self):
        cams = [
            Camera(name="Camera 1", current_ip="192.168.1.10", mac_address="aa:bb:cc:dd:ee:01"),
            Camera(name="Camera 2", current_ip="192.168.1.20", mac_address="aa:bb:cc:dd:ee:02"),
        ]
        self.assertTrue(self.storage.save_cameras(cams))

        loaded = self.storage.load_cameras()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].name, "Camera 1")
        self.assertEqual(loaded[0].current_ip, "192.168.1.10")
        self.assertEqual(loaded[0].mac_address, "aa:bb:cc:dd:ee:01")
        self.assertEqual(loaded[1].name, "Camera 2")
        self.assertEqual(loaded[1].current_ip, "192.168.1.20")

    def test_get_default_config_dir_platforms(self):
        # Simula Windows
        with patch.object(sys, "platform", "win32"), patch.dict(os.environ, {"APPDATA": "/fake/appdata"}):
            dir_win = get_default_config_dir()
            self.assertEqual(str(dir_win), "/fake/appdata/myipcams")

        # Simula macOS
        with patch.object(sys, "platform", "darwin"):
            dir_mac = get_default_config_dir()
            self.assertIn("Library/Application Support/myipcams", str(dir_mac))

        # Simula Linux com XDG_CONFIG_HOME
        with patch.object(sys, "platform", "linux"), patch.dict(os.environ, {"XDG_CONFIG_HOME": "/fake/config"}):
            dir_linux = get_default_config_dir()
            self.assertEqual(str(dir_linux), "/fake/config/myipcams")


if __name__ == "__main__":
    unittest.main()

