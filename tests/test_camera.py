import unittest
from myipcams.core.camera import Camera


class TestCameraModel(unittest.TestCase):
    def test_rtsp_url_simple(self):
        cam = Camera(current_ip="192.168.1.10", rtsp_port=554, rtsp_path="/live/ch0")
        self.assertEqual(cam.get_rtsp_url(), "rtsp://192.168.1.10:554/live/ch0")

    def test_rtsp_url_with_credentials(self):
        cam = Camera(
            current_ip="192.168.1.50",
            rtsp_port=8554,
            rtsp_path="live/main",
            username="admin",
            password="secretpassword123",
        )
        self.assertEqual(
            cam.get_rtsp_url(),
            "rtsp://admin:secretpassword123@192.168.1.50:8554/live/main"
        )

    def test_update_ip(self):
        cam = Camera(current_ip="192.168.1.10")
        self.assertFalse(cam.update_ip("192.168.1.10"))
        self.assertTrue(cam.update_ip("192.168.1.25"))
        self.assertEqual(cam.current_ip, "192.168.1.25")
        self.assertIsNotNone(cam.last_seen)

    def test_serialization(self):
        cam = Camera(
            name="Entrada",
            mac_address="AA:BB:CC:11:22:33",
            current_ip="192.168.0.88",
            rtsp_port=554,
            username="admin",
            password="123",
        )
        d = cam.to_dict()
        self.assertEqual(d["mac_address"], "aa:bb:cc:11:22:33")

        restored = Camera.from_dict(d)
        self.assertEqual(restored.name, "Entrada")
        self.assertEqual(restored.mac_address, "aa:bb:cc:11:22:33")
        self.assertEqual(restored.current_ip, "192.168.0.88")
        self.assertEqual(restored.camera_type, "generic")
        self.assertEqual(restored.xm_port, 34567)

    def test_legacy_dict_compatibility(self):
        # Dicionário legado sem campos camera_type e xm_port
        legacy_dict = {
            "id": "test-id-123",
            "name": "Câmera Antiga",
            "current_ip": "192.168.1.200",
            "rtsp_port": 554,
            "rtsp_path": "/live/ch0",
        }
        cam = Camera.from_dict(legacy_dict)
        self.assertEqual(cam.camera_type, "generic")
        self.assertEqual(cam.xm_port, 34567)

    def test_icsee_camera_properties(self):
        cam = Camera(
            name="Câmera iCSee",
            camera_type="icsee",
            xm_port=34567,
        )
        d = cam.to_dict()
        self.assertEqual(d["camera_type"], "icsee")
        self.assertEqual(d["xm_port"], 34567)
        restored = Camera.from_dict(d)
        self.assertEqual(restored.camera_type, "icsee")
        self.assertEqual(restored.xm_port, 34567)


if __name__ == "__main__":
    unittest.main()
