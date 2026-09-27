import unittest
from unittest.mock import patch
from myipcams.core.camera import Camera
from myipcams.core.tracker import IPTracker


class TestTracker(unittest.TestCase):
    def test_tracker_detects_ip_change_via_arp(self):
        cam = Camera(
            name="Câmera Garagem",
            current_ip="192.168.1.100",
            mac_address="a4:12:42:3b:01:2c"
        )
        cameras = [cam]

        changed_events = []
        def on_ip_changed(camera, old_ip, new_ip):
            changed_events.append((camera.name, old_ip, new_ip))

        tracker = IPTracker(
            get_cameras_fn=lambda: cameras,
            on_ip_changed=on_ip_changed,
            check_interval=60.0
        )

        # Simula que a tabela ARP agora tem o IP 192.168.1.150 para o mesmo MAC
        with patch("myipcams.core.tracker.ARPTable.get_mac_to_ip_map") as mock_arp:
            mock_arp.return_value = {"a4:12:42:3b:01:2c": "192.168.1.150"}
            tracker.check_all_cameras()

        self.assertEqual(len(changed_events), 1)
        self.assertEqual(changed_events[0], ("Câmera Garagem", "192.168.1.100", "192.168.1.150"))
        self.assertEqual(cam.current_ip, "192.168.1.150")


if __name__ == "__main__":
    unittest.main()
