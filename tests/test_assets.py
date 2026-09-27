import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from myipcams.ui.assets import (
    get_project_root,
    get_asset_path,
    get_app_icon,
    get_camera_animation_path,
    get_camera_video_path,
)

# Garante instância única de QApplication para testes com Qt em modo headless
app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestAssets(unittest.TestCase):
    def test_project_root(self):
        root = get_project_root()
        self.assertTrue((root / "pyproject.toml").is_file())
        self.assertTrue((root / "assets").is_dir())

    def test_asset_resolution(self):
        icon_path = get_asset_path("myipcams.png")
        self.assertIsNotNone(icon_path)
        self.assertTrue(icon_path.is_file())

    def test_app_icon_valid(self):
        icon = get_app_icon()
        self.assertFalse(icon.isNull())
        # Testa se tem tamanhos disponíveis
        sizes = icon.availableSizes()
        self.assertTrue(len(sizes) > 0)

    def test_animation_and_video_paths(self):
        anim = get_camera_animation_path()
        self.assertIsNotNone(anim)
        self.assertTrue(os.path.isfile(anim))

        video = get_camera_video_path()
        self.assertIsNotNone(video)
        self.assertTrue(os.path.isfile(video))


if __name__ == "__main__":
    unittest.main()
