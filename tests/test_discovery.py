import unittest
from myipcams.network.discovery import NetworkDiscovery, DiscoveredCamera


SAMPLE_PROBE_MATCH = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
                   xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
                   xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
    <SOAP-ENV:Header>
        <wsa:MessageID>urn:uuid:7c0e81c0-2f3b-11b2-a000-001213141516</wsa:MessageID>
        <wsa:RelatesTo>urn:uuid:12345678-1234-1234-1234-123456789abc</wsa:RelatesTo>
        <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
        <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/ProbeMatches</wsa:Action>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
        <d:ProbeMatches>
            <d:ProbeMatch>
                <wsa:EndpointReference>
                    <wsa:Address>urn:uuid:a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d</wsa:Address>
                </wsa:EndpointReference>
                <d:Types>dn:NetworkVideoTransmitter</d:Types>
                <d:Scopes>
                    onvif://www.onvif.org/type/video_encoder
                    onvif://www.onvif.org/name/Camera%20Garagem
                    onvif://www.onvif.org/hardware/IPC-HDW2431T
                    onvif://www.onvif.org/location/Casa
                </d:Scopes>
                <d:XAddrs>
                    http://192.168.1.188:80/onvif/device_service
                </d:XAddrs>
                <d:MetadataVersion>1</d:MetadataVersion>
            </d:ProbeMatch>
        </d:ProbeMatches>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


class TestDiscovery(unittest.TestCase):
    def test_parse_ws_probe_match(self):
        cam = NetworkDiscovery._parse_ws_probe_match(SAMPLE_PROBE_MATCH, "192.168.1.188")
        self.assertIsNotNone(cam)
        self.assertEqual(cam.ip, "192.168.1.188")
        self.assertEqual(cam.port, 80)
        self.assertEqual(cam.uuid, "urn:uuid:a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")
        self.assertEqual(cam.name, "Camera Garagem")
        self.assertEqual(cam.hardware, "IPC-HDW2431T")
        self.assertEqual(cam.protocol, "ONVIF")
        self.assertEqual(cam.rtsp_port, 554)
        self.assertIn(80, cam.open_ports)

    def test_parse_ws_probe_match_stale_xaddrs_ip(self):
        # Quando a câmera anuncia um IP desatualizado/fábrica (ex: 192.168.1.10 no XAddrs),
        # mas o pacote UDP veio do IP real da sub-rede (ex: 192.168.10.25)
        stale_xml = SAMPLE_PROBE_MATCH.replace("192.168.1.188:80", "192.168.1.10:8899")
        cam = NetworkDiscovery._parse_ws_probe_match(stale_xml, "192.168.10.25")
        self.assertIsNotNone(cam)
        self.assertEqual(cam.ip, "192.168.10.25")
        self.assertEqual(cam.port, 8899)
        self.assertEqual(cam.xaddrs, "http://192.168.10.25:8899/onvif/device_service")

    def test_fix_xaddrs_ip(self):
        original = "http://192.168.1.10:8899/onvif/device_service http://192.168.1.10/onvif/media"
        fixed = NetworkDiscovery._fix_xaddrs_ip(original, "192.168.10.25")
        self.assertEqual(
            fixed,
            "http://192.168.10.25:8899/onvif/device_service http://192.168.10.25/onvif/media"
        )

    def test_get_primary_subnet(self):
        subnet = NetworkDiscovery.get_primary_subnet()
        self.assertIsInstance(subnet, str)
        self.assertIn("/", subnet)

    def test_discovered_camera_display_string(self):
        cam = DiscoveredCamera(
            ip="192.168.1.200",
            port=80,
            rtsp_port=554,
            mac="aa:bb:cc:dd:ee:ff",
            name="Camera Sala",
            hardware="Hikvision RTSP Server",
            open_ports=[554, 80],
        )
        display = cam.to_display_string()
        self.assertIn("192.168.1.200", display)
        self.assertIn("Camera Sala", display)
        self.assertIn("Hikvision RTSP Server", display)
        self.assertIn("554,80", display)
        self.assertIn("aa:bb:cc:dd:ee:ff", display)

    def test_discover_all_merging(self):
        from unittest.mock import patch

        cam_onvif = DiscoveredCamera(
            ip="192.168.1.50",
            port=80,
            mac=None,
            name="ONVIF Cam",
            protocol="ONVIF",
            open_ports=[80],
        )
        cam_subnet = DiscoveredCamera(
            ip="192.168.1.50",
            port=80,
            mac="aa:bb:cc:11:22:33",
            name="Câmera RTSP (192.168.1.50)",
            hardware="Hikvision",
            protocol="RTSP",
            open_ports=[554, 80],
        )
        cam_unique = DiscoveredCamera(
            ip="192.168.1.51",
            port=554,
            mac="11:22:33:44:55:66",
            name="Câmera RTSP (192.168.1.51)",
            protocol="RTSP",
            open_ports=[554],
        )

        with patch.object(NetworkDiscovery, "discover_onvif", return_value=[cam_onvif]):
            with patch.object(NetworkDiscovery, "scan_subnet", return_value=[cam_subnet, cam_unique]):
                results = NetworkDiscovery.discover_all(subnet_str="192.168.1.0/24", run_subnet_scan=True)
                self.assertEqual(len(results), 2)
                res_map = {c.ip: c for c in results}
                merged = res_map["192.168.1.50"]
                self.assertEqual(merged.mac, "aa:bb:cc:11:22:33")
                self.assertEqual(merged.hardware, "Hikvision")
                self.assertIn(554, merged.open_ports)
                self.assertIn(80, merged.open_ports)
                self.assertEqual(merged.protocol, "ONVIF + RTSP")

                # Câmera descoberta apenas via varredura de sub-rede
                self.assertIn("192.168.1.51", res_map)
                self.assertEqual(res_map["192.168.1.51"].mac, "11:22:33:44:55:66")

    def test_get_local_subnets_windows_parsing(self):
        import subprocess
        import sys
        from unittest.mock import patch, MagicMock

        windows_ipconfig = """
Windows IP Configuration

Ethernet adapter Ethernet:
   Connection-specific DNS Suffix  . :
   Link-local IPv6 Address . . . . . : fe80::1
   IPv4 Address. . . . . . . . . . . : 192.168.1.150
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
"""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = windows_ipconfig

        with patch.object(sys, "platform", "win32"), patch.object(subprocess, "run", return_value=mock_res):
            subnets = NetworkDiscovery.get_local_subnets()
            self.assertIn("192.168.1.0/24", subnets)

    def test_get_local_subnets_macos_parsing(self):
        import subprocess
        import sys
        from unittest.mock import patch, MagicMock

        macos_ifconfig = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	ether a4:83:e7:22:11:00
	inet 192.168.15.22 netmask 0xffffff00 broadcast 192.168.15.255
"""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = macos_ifconfig

        with patch.object(sys, "platform", "darwin"), patch.object(subprocess, "run", return_value=mock_res):
            subnets = NetworkDiscovery.get_local_subnets()
            self.assertIn("192.168.15.0/24", subnets)


if __name__ == "__main__":
    unittest.main()

