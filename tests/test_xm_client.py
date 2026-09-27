import json
import unittest
from unittest.mock import MagicMock, patch

from myipcams.network.xm_client import (
    sofia_hash,
    pack_message,
    unpack_header,
    SOFIA_MAGIC,
    HEADER_SIZE,
    MSG_LOGIN_REQ,
    MSG_LOGIN_RSP,
    MSG_PTZ_REQ,
    MSG_PTZ_RSP,
    XMClient,
    probe_device,
)


class TestXMClient(unittest.TestCase):
    def test_sofia_hash_empty(self):
        self.assertEqual(sofia_hash(""), "")

    def test_sofia_hash_standard(self):
        # O hash Sofia para qualquer senha não vazia deve ter 8 caracteres alfanuméricos
        h1 = sofia_hash("admin")
        self.assertEqual(len(h1), 8)
        self.assertTrue(h1.isalnum())

        h2 = sofia_hash("123456")
        self.assertEqual(len(h2), 8)
        self.assertTrue(h2.isalnum())
        self.assertNotEqual(h1, h2)

        # Idempotência
        self.assertEqual(sofia_hash("admin"), h1)

    def test_pack_and_unpack(self):
        payload = {"TestKey": "TestValue", "Number": 42}
        packet = pack_message(
            msg_id=MSG_LOGIN_REQ,
            session_id=123,
            seq_num=1,
            payload=payload,
        )

        # Tamanho total = 20 bytes de cabeçalho + tamanho do payload
        self.assertGreater(len(packet), HEADER_SIZE)
        self.assertEqual(packet[0], SOFIA_MAGIC)

        # Desempacota cabeçalho
        session_id, seq_num, msg_id, body_len = unpack_header(packet[:HEADER_SIZE])
        self.assertEqual(session_id, 123)
        self.assertEqual(seq_num, 1)
        self.assertEqual(msg_id, MSG_LOGIN_REQ)

        # Verifica corpo
        body_bytes = packet[HEADER_SIZE : HEADER_SIZE + body_len]
        decoded = json.loads(body_bytes.decode("utf-8").strip().rstrip("\x00"))
        self.assertEqual(decoded["TestKey"], "TestValue")
        self.assertEqual(decoded["Number"], 42)

    def test_unpack_invalid_magic(self):
        bad_header = b"\x00" * HEADER_SIZE
        with self.assertRaises(ValueError):
            unpack_header(bad_header)

    def test_unpack_too_short(self):
        with self.assertRaises(ValueError):
            unpack_header(b"\xFF\x00")

    @patch("socket.socket")
    def test_client_login_success(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        client = XMClient(ip="192.168.1.100", port=34567, username="admin", password="123")

        # Mock da resposta de login da câmera
        rsp_payload = {"Ret": 100, "SessionID": "0x0000000a"}
        rsp_packet = pack_message(MSG_LOGIN_RSP, 10, 1, rsp_payload)

        # Configura socket.recv para retornar cabeçalho e depois corpo
        mock_sock.recv.side_effect = [
            rsp_packet[:HEADER_SIZE],
            rsp_packet[HEADER_SIZE:],
        ]

        success = client.login()
        self.assertTrue(success)
        self.assertEqual(client.session_id, 10)

    @patch("socket.socket")
    def test_client_ptz_control(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        client = XMClient(ip="192.168.1.100", port=34567)
        client.session_id = 5
        client._sock = mock_sock

        # Mock da resposta do PTZ
        rsp_payload = {"Ret": 100, "SessionID": "0x5"}
        rsp_packet = pack_message(MSG_PTZ_RSP, 5, 1, rsp_payload)

        mock_sock.recv.side_effect = [
            rsp_packet[:HEADER_SIZE],
            rsp_packet[HEADER_SIZE:],
        ]

        result = client.ptz_control("up", speed=6)
        self.assertTrue(result)
        self.assertTrue(mock_sock.sendall.called)

        # Verifica comando enviado
        sent_bytes = mock_sock.sendall.call_args[0][0]
        body = sent_bytes[HEADER_SIZE:].decode("utf-8").strip().rstrip("\x00")
        sent_json = json.loads(body)
        self.assertEqual(sent_json["OPPTZControl"]["Command"], "DirectionUp")
        self.assertEqual(sent_json["OPPTZControl"]["Parameter"]["Step"], 6)

    @patch("socket.socket")
    def test_probe_device_success(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        # Retorna cabeçalho que começa com SOFIA_MAGIC
        mock_sock.recv.return_value = bytes([SOFIA_MAGIC]) + b"\x00" * 19

        self.assertTrue(probe_device("192.168.1.50", 34567))

    @patch("socket.socket")
    def test_probe_device_failure(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")

        self.assertFalse(probe_device("192.168.1.50", 34567))


if __name__ == "__main__":
    unittest.main()
