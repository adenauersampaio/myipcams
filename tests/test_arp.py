import unittest
from myipcams.network.arp import normalize_mac, parse_arp_output, ARPTable


class TestARP(unittest.TestCase):
    def test_normalize_mac(self):
        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("aabb.ccdd.eeff"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("AABBCCDDEEFF"), "aa:bb:cc:dd:ee:ff")
        # Suporte a formato BSD/macOS com octetos sem zero à esquerda
        self.assertEqual(normalize_mac("0:14:22:1:23:45"), "00:14:22:01:23:45")
        self.assertIsNone(normalize_mac("invalid-mac"))
        self.assertIsNone(normalize_mac(""))
        self.assertIsNone(normalize_mac(None))

    def test_parse_arp_output_windows(self):
        windows_sample = """
Interface: 192.168.1.50 --- 0x14
  Internet Address      Physical Address      Type
  192.168.1.1           00-14-22-01-23-45     dynamic
  192.168.1.120         a4-12-42-3b-01-2c     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
"""
        parsed = parse_arp_output(windows_sample)
        self.assertEqual(parsed.get("00:14:22:01:23:45"), "192.168.1.1")
        self.assertEqual(parsed.get("a4:12:42:3b:01:2c"), "192.168.1.120")
        self.assertNotIn("ff:ff:ff:ff:ff:ff", parsed)

    def test_parse_arp_output_macos(self):
        macos_sample = """
? (192.168.1.1) at 0:14:22:1:23:45 on en0 ifscope [ethernet]
? (192.168.1.130) at a4:12:42:3b:1:2c on en0 ifscope [ethernet]
? (192.168.1.255) at (incomplete) on en0 ifscope [ethernet]
"""
        parsed = parse_arp_output(macos_sample)
        self.assertEqual(parsed.get("00:14:22:01:23:45"), "192.168.1.1")
        self.assertEqual(parsed.get("a4:12:42:3b:01:2c"), "192.168.1.130")

    def test_get_mac_to_ip_map_returns_dict(self):
        result = ARPTable.get_mac_to_ip_map()
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()

