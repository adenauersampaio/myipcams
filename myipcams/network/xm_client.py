import hashlib
import json
import logging
import socket
import struct
import threading
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Constantes do Protocolo Sofia/NETip
SOFIA_MAGIC = 0xFF
SOFIA_VERSION = 0x00
HEADER_FORMAT = "<BB2sIIBBHI"
HEADER_SIZE = 20

# Message IDs comuns
MSG_LOGIN_REQ = 1000        # 0x03E8
MSG_LOGIN_RSP = 1001        # 0x03E9
MSG_CONFIG_GET_REQ = 1042   # 0x0412
MSG_CONFIG_GET_RSP = 1043   # 0x0413
MSG_CONFIG_SET_REQ = 1040   # 0x0410
MSG_CONFIG_SET_RSP = 1041   # 0x0411
MSG_PTZ_REQ = 1400          # 0x0578
MSG_PTZ_RSP = 1401          # 0x0579
MSG_OP_MACHINE_REQ = 1450   # 0x05AA
MSG_OP_MACHINE_RSP = 1451   # 0x05AB
MSG_TALK_REQ = 1420         # 0x058C
MSG_TALK_RSP = 1421         # 0x058D

PTZ_COMMANDS = {
    "up": "DirectionUp",
    "down": "DirectionDown",
    "left": "DirectionLeft",
    "right": "DirectionRight",
    "up_left": "DirectionLeftUp",
    "left_up": "DirectionLeftUp",
    "up_right": "DirectionRightUp",
    "right_up": "DirectionRightUp",
    "down_left": "DirectionLeftDown",
    "left_down": "DirectionLeftDown",
    "down_right": "DirectionRightDown",
    "right_down": "DirectionRightDown",
    "stop": "PTZStop",
}


def sofia_hash(password: str) -> str:
    """Calcula o hash de autenticação da senha para o protocolo Xiongmai Sofia/NETip.
    
    Gera uma string de 8 caracteres alfanuméricos derivada do digest MD5 da senha.
    """
    if not password:
        return ""
    md5_digest = hashlib.md5(password.encode("utf-8")).digest()
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "".join([chars[sum(pair) % 62] for pair in zip(md5_digest[::2], md5_digest[1::2])])


def pack_message(msg_id: int, session_id: int, seq_num: int, payload: Dict[str, Any]) -> bytes:
    """Empacota um dicionário JSON no formato binário de 20 bytes do protocolo Sofia."""
    body_str = json.dumps(payload, separators=(',', ':')) + "\n\x00"
    body_bytes = body_str.encode("utf-8")
    body_len = len(body_bytes)

    header = struct.pack(
        HEADER_FORMAT,
        SOFIA_MAGIC,
        SOFIA_VERSION,
        b"\x00\x00",
        session_id,
        seq_num,
        0,  # total packets
        0,  # current packet
        msg_id,
        body_len,
    )
    return header + body_bytes


def unpack_header(data: bytes) -> Tuple[int, int, int, int]:
    """Desempacota o cabeçalho de 20 bytes.
    Retorna: (session_id, seq_num, msg_id, body_length)
    """
    if len(data) < HEADER_SIZE:
        raise ValueError(f"Cabeçalho incompleto ({len(data)} bytes, esperado {HEADER_SIZE})")

    magic, version, _, session_id, seq_num, _, _, msg_id, body_len = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )
    if magic != SOFIA_MAGIC:
        raise ValueError(f"Byte mágico inválido: {hex(magic)} (esperado {hex(SOFIA_MAGIC)})")

    return session_id, seq_num, msg_id, body_len


def _recv_exact(sock: socket.socket, length: int) -> Optional[bytes]:
    """Recebe exatamente N bytes de um socket, contornando fragmentação TCP."""
    buf = bytearray()
    while len(buf) < length:
        try:
            chunk = sock.recv(length - len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        except Exception:
            return None
    return bytes(buf)


def probe_device(ip: str, port: int = 34567, timeout: float = 1.5) -> bool:
    """Testa se o dispositivo no IP e porta especificados responde ao protocolo Xiongmai Sofia."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        probe_payload = {
            "EncryptType": "MD5",
            "LoginType": "DVRIP-Web",
            "PassWord": "",
            "UserName": "admin"
        }
        packet = pack_message(MSG_LOGIN_REQ, 0, 0, probe_payload)
        sock.sendall(packet)

        header_bytes = _recv_exact(sock, HEADER_SIZE)
        sock.close()

        if header_bytes and len(header_bytes) >= HEADER_SIZE and header_bytes[0] == SOFIA_MAGIC:
            return True
        return False
    except Exception as e:
        logger.debug(f"Sonda Xiongmai falhou para {ip}:{port}: {e}")
        return False


class XMClient:
    """Cliente para controle de câmeras Xiongmai / iCSee via protocolo Sofia/NETip (porta 34567)."""

    def __init__(self, ip: str, port: int = 34567, username: str = "admin", password: str = "", timeout: float = 3.0):
        self.ip = ip
        self.port = port
        self.username = username or "admin"
        self.password = password or ""
        self.timeout = timeout
        self.session_id: int = 0
        self.seq_num: int = 0
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._last_direction = "DirectionUp"

    def connect(self) -> bool:
        """Conecta ao socket TCP da câmera."""
        self.disconnect()
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.ip, self.port))
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar a {self.ip}:{self.port}: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Fecha a conexão com a câmera."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _send_and_receive(self, msg_id: int, payload: Dict[str, Any], retry: bool = True) -> Optional[Dict[str, Any]]:
        """Envia uma mensagem empacotada e aguarda a resposta JSON com proteção de concorrência."""
        with self._lock:
            if not self._sock:
                if not self.connect():
                    return None

            self.seq_num += 1
            packet = pack_message(msg_id, self.session_id, self.seq_num, payload)

            try:
                self._sock.sendall(packet)
                header_bytes = _recv_exact(self._sock, HEADER_SIZE)
                if not header_bytes or len(header_bytes) < HEADER_SIZE:
                    raise OSError("Resposta de cabeçalho incompleta ou socket fechado")

                resp_session, _, resp_msg, body_len = unpack_header(header_bytes)
                if resp_session and not self.session_id:
                    self.session_id = resp_session

                # Lê o corpo completo da resposta
                body_bytes = _recv_exact(self._sock, body_len)
                if not body_bytes:
                    return None

                raw_body = body_bytes.decode("utf-8", errors="ignore").strip().rstrip("\x00")
                if not raw_body:
                    return None

                return json.loads(raw_body)
            except Exception as e:
                logger.warning(f"Comunicação com {self.ip}:{self.port} falhou ({e}). Tentando reconectar...")
                self.disconnect()
                if retry and msg_id != MSG_LOGIN_REQ:
                    # Tenta reconectar e re-autenticar uma vez
                    if self._internal_login():
                        return self._send_and_receive(msg_id, payload, retry=False)
                return None

    def _internal_login(self) -> bool:
        """Executa login sem adquirir novo lock externo."""
        if not self._sock:
            if not self.connect():
                return False

        hashed_pass = sofia_hash(self.password)
        login_payload = {
            "EncryptType": "MD5",
            "LoginType": "DVRIP-Web",
            "PassWord": hashed_pass,
            "UserName": self.username
        }

        self.seq_num += 1
        packet = pack_message(MSG_LOGIN_REQ, 0, self.seq_num, login_payload)
        try:
            self._sock.sendall(packet)
            header_bytes = _recv_exact(self._sock, HEADER_SIZE)
            if not header_bytes:
                return False
            resp_session, _, _, body_len = unpack_header(header_bytes)
            body_bytes = _recv_exact(self._sock, body_len)
            if not body_bytes:
                return False
            raw = body_bytes.decode("utf-8", errors="ignore").strip().rstrip("\x00")
            resp = json.loads(raw)
            if resp.get("Ret") == 100:
                session_str = resp.get("SessionID")
                if session_str and isinstance(session_str, str) and session_str.startswith("0x"):
                    try:
                        self.session_id = int(session_str, 16)
                    except ValueError:
                        self.session_id = resp_session or 1
                else:
                    self.session_id = resp_session or 1
                return True
            return False
        except Exception:
            self.disconnect()
            return False

    def login(self) -> bool:
        """Realiza autenticação com a câmera."""
        with self._lock:
            return self._internal_login()

    def ensure_connected(self) -> bool:
        """Garante que o cliente está conectado e autenticado."""
        if self._sock and self.session_id:
            return True
        return self.login()

    def ptz_control(self, direction: str, speed: int = 4, channel: int = 0) -> bool:
        """Envia um comando de movimentação PTZ.
        
        Args:
            direction: 'up', 'down', 'left', 'right', 'up_left', 'up_right',
                       'down_left', 'down_right', 'stop'
            speed: 1 a 8 (padrão 4)
            channel: canal da câmera (normalmente 0)
        """
        cmd_name = PTZ_COMMANDS.get(direction.lower(), "DirectionUp")
        self._last_direction = cmd_name

        if not self.ensure_connected():
            return False

        # Parâmetros padrão completos exigidos pelo firmware Xiongmai/Sofia
        parms = {
            "AUX": {"Number": 0, "Status": "On"},
            "Channel": channel,
            "MenuOpts": "Enter",
            "POINT": {"bottom": 0, "left": 0, "right": 0, "top": 0},
            "Pattern": "SetBegin",
            "Preset": 65535,
            "Step": max(1, min(8, speed)),
            "Tour": 0,
        }

        # Formatação obrigatória de 8 dígitos hexadecimais para o SessionID
        session_formatted = f"0x{self.session_id:08X}"
        ptz_payload = {
            "Name": "OPPTZControl",
            "OPPTZControl": {
                "Command": cmd_name,
                "Parameter": parms,
            },
            "SessionID": session_formatted,
        }

        resp = self._send_and_receive(MSG_PTZ_REQ, ptz_payload)
        if resp and resp.get("Ret") == 100:
            return True
        return False

    def ptz_stop(self, channel: int = 0) -> bool:
        """Para o movimento PTZ imediatamente."""
        if not self.ensure_connected():
            return False

        session_formatted = f"0x{self.session_id:08X}"
        cmd_name = self._last_direction or "DirectionUp"

        # 1. Parada via Preset -1 no comando ativo (método padrão Xiongmai)
        parms_stop = {
            "AUX": {"Number": 0, "Status": "On"},
            "Channel": channel,
            "MenuOpts": "Enter",
            "POINT": {"bottom": 0, "left": 0, "right": 0, "top": 0},
            "Pattern": "SetBegin",
            "Preset": -1,
            "Step": 0,
            "Tour": 0,
        }
        ptz_payload = {
            "Name": "OPPTZControl",
            "OPPTZControl": {
                "Command": cmd_name,
                "Parameter": parms_stop,
            },
            "SessionID": session_formatted,
        }
        resp = self._send_and_receive(MSG_PTZ_REQ, ptz_payload)

        # 2. Envio complementar com PTZStop para compatibilidade ampla
        ptz_stop_fallback = {
            "Name": "OPPTZControl",
            "OPPTZControl": {
                "Command": "PTZStop",
                "Parameter": {
                    "Channel": channel,
                    "Step": 0,
                },
            },
            "SessionID": session_formatted,
        }
        self._send_and_receive(MSG_PTZ_REQ, ptz_stop_fallback)

        return bool(resp and resp.get("Ret") == 100)

    def get_alarm_config(self) -> Dict[str, Any]:
        """Obtém as configurações de alarme (movimento e humanos) da câmera."""
        if not self.ensure_connected():
            return {}

        results = {}
        session_formatted = f"0x{self.session_id:08X}"

        # 1. Detecção de Movimento (MotionDetect)
        motion_req = {
            "Name": "Detect.MotionDetect",
            "SessionID": session_formatted,
        }
        resp_motion = self._send_and_receive(MSG_CONFIG_GET_REQ, motion_req)
        if resp_motion and resp_motion.get("Ret") == 100:
            results["motion"] = resp_motion.get("Detect.MotionDetect", [])

        # 2. Detecção Humana / IA (HumanDetect)
        human_req = {
            "Name": "Detect.HumanDetect",
            "SessionID": session_formatted,
        }
        resp_human = self._send_and_receive(MSG_CONFIG_GET_REQ, human_req)
        if resp_human and resp_human.get("Ret") == 100:
            results["human"] = resp_human.get("Detect.HumanDetect", [])

        return results

    def set_motion_detection(self, enable: bool, level: int = 3) -> bool:
        """Ativa ou desativa a detecção de movimento tradicional."""
        if not self.ensure_connected():
            return False

        current = self.get_alarm_config().get("motion", [])
        if current and isinstance(current, list):
            motion_data = current[0]
        else:
            motion_data = {}

        motion_data["Enable"] = enable
        motion_data["Level"] = max(1, min(6, level))

        session_formatted = f"0x{self.session_id:08X}"
        payload = {
            "Name": "Detect.MotionDetect",
            "SessionID": session_formatted,
            "Detect.MotionDetect": [motion_data]
        }
        resp = self._send_and_receive(MSG_CONFIG_SET_REQ, payload)
        return bool(resp and resp.get("Ret") == 100)

    def set_human_detection(self, enable: bool) -> bool:
        """Ativa ou desativa a detecção de silhueta humana por IA."""
        if not self.ensure_connected():
            return False

        current = self.get_alarm_config().get("human", [])
        if current and isinstance(current, list):
            human_data = current[0]
        else:
            human_data = {}

        human_data["Enable"] = enable

        session_formatted = f"0x{self.session_id:08X}"
        payload = {
            "Name": "Detect.HumanDetect",
            "SessionID": session_formatted,
            "Detect.HumanDetect": [human_data]
        }
        resp = self._send_and_receive(MSG_CONFIG_SET_REQ, payload)
        return bool(resp and resp.get("Ret") == 100)

    def reboot(self) -> bool:
        """Envia comando de reinicialização (reboot) para a câmera Xiongmai / iCSee."""
        if not self.ensure_connected():
            return False

        session_formatted = f"0x{self.session_id:08X}"
        payload = {
            "Name": "OPMachine",
            "OPMachine": {
                "Action": "Reboot"
            },
            "SessionID": session_formatted,
        }

        try:
            resp = self._send_and_receive(MSG_OP_MACHINE_REQ, payload)
            if resp and resp.get("Ret") == 100:
                logger.info(f"Comando de reboot Xiongmai enviado com sucesso para {self.ip}:{self.port}")
                return True
        except Exception as e:
            logger.debug(f"Exceção durante envio de reboot Xiongmai via MSG_OP_MACHINE_REQ: {e}")

        # Se falhou via MSG_OP_MACHINE_REQ, tenta via MSG_CONFIG_SET_REQ como fallback
        try:
            resp_fallback = self._send_and_receive(MSG_CONFIG_SET_REQ, payload)
            if resp_fallback and resp_fallback.get("Ret") == 100:
                logger.info(f"Comando de reboot Xiongmai (fallback) enviado com sucesso para {self.ip}:{self.port}")
                return True
        except Exception:
            pass

        return False

    def check_talk_support(self) -> bool:
        """Verifica se a câmera suporta intercomunicador de voz (bidirecional)."""
        if not self.ensure_connected():
            return False

        session_formatted = f"0x{self.session_id:08X}"
        payload = {
            "Name": "SystemFunction",
            "SessionID": session_formatted,
        }
        try:
            resp = self._send_and_receive(MSG_CONFIG_GET_REQ, payload)
            if resp and resp.get("Ret") == 100:
                sys_func = resp.get("SystemFunction", {})
                if sys_func.get("Talk") or sys_func.get("AudioFunction", {}).get("Talk"):
                    return True
        except Exception:
            pass

        return False
