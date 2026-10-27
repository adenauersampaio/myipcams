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

    def test_tracker_detects_ip_and_mac_change_via_serial_number(self):
        from myipcams.network.discovery import DiscoveredCamera

        cam = Camera(
            name="Câmera Wi-Fi XMeye",
            serial_number="c907717f3a5f1ef2",
            current_ip="192.168.1.20",
            mac_address="9a:39:71:11:22:33"  # MAC antigo
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

        # Câmera mudou tanto de MAC quanto de IP no roteador
        new_disc = DiscoveredCamera(
            ip="192.168.1.88",
            mac="9a:39:71:aa:bb:cc",  # Novo MAC alternado
            serial_number="c907717f3a5f1ef2",  # Serial idêntico
            hardware="XM533"
        )

        with patch("myipcams.core.tracker.ARPTable.get_mac_to_ip_map") as mock_arp, \
             patch("myipcams.core.tracker.NetworkDiscovery.discover_onvif") as mock_onvif, \
             patch("myipcams.core.tracker.NetworkDiscovery.fetch_device_info") as mock_info:
            mock_arp.return_value = {}  # MAC antigo não está mais no ARP
            mock_onvif.return_value = [new_disc]
            mock_info.return_value = (None, None, None)

            tracker.check_all_cameras()

        self.assertEqual(len(changed_events), 1)
        self.assertEqual(changed_events[0], ("Câmera Wi-Fi XMeye", "192.168.1.20", "192.168.1.88"))
        self.assertEqual(cam.current_ip, "192.168.1.88")
        self.assertEqual(cam.mac_address, "9a:39:71:aa:bb:cc")  # MAC atualizado!


if __name__ == "__main__":
    unittest.main()
