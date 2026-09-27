from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


@dataclass
class Camera:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Nova Câmera"
    mac_address: Optional[str] = None      # ex: "a4:12:42:3b:01:2c" (identificador físico imutável)
    onvif_uuid: Optional[str] = None       # ex: "urn:uuid:48b0a... (identificador ONVIF)
    current_ip: str = "192.168.1.100"
    rtsp_port: int = 554
    rtsp_path: str = "/live/ch0"          # Padrão comum; varia por fabricante (/h264Preview_01_main, /onvif1, etc.)
    username: str = ""
    password: str = ""
    onvif_port: int = 80
    enabled: bool = True
    status: str = "offline"               # "online", "reconnecting", "offline"
    last_seen: Optional[str] = None
    vendor_model: Optional[str] = None
    camera_type: str = "generic"          # "generic" (RTSP padrão) ou "icsee" (Xiongmai com PTZ/Alarmes)
    xm_port: int = 34567                  # Porta de controle Xiongmai Sofia/NETip (padrão 34567)

    def get_rtsp_url(self) -> str:
        """Gera a URL completa do stream RTSP usando o IP atual e credenciais."""
        auth = ""
        if self.username:
            if self.password:
                auth = f"{self.username}:{self.password}@"
            else:
                auth = f"{self.username}@"

        path = self.rtsp_path.strip()
        if not path.startswith("/"):
            path = "/" + path

        return f"rtsp://{auth}{self.current_ip}:{self.rtsp_port}{path}"

    def update_ip(self, new_ip: str) -> bool:
        """Atualiza o IP atual se tiver mudado. Retorna True se houve mudança."""
        new_ip = new_ip.strip()
        if new_ip and new_ip != self.current_ip:
            self.current_ip = new_ip
            self.last_seen = datetime.now().isoformat()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mac_address": self.mac_address.lower() if self.mac_address else None,
            "onvif_uuid": self.onvif_uuid,
            "current_ip": self.current_ip,
            "rtsp_port": self.rtsp_port,
            "rtsp_path": self.rtsp_path,
            "username": self.username,
            "password": self.password,
            "onvif_port": self.onvif_port,
            "enabled": self.enabled,
            "vendor_model": self.vendor_model,
            "last_seen": self.last_seen,
            "camera_type": self.camera_type,
            "xm_port": self.xm_port,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Camera":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Câmera"),
            mac_address=data.get("mac_address", "").lower() if data.get("mac_address") else None,
            onvif_uuid=data.get("onvif_uuid"),
            current_ip=data.get("current_ip", "127.0.0.1"),
            rtsp_port=int(data.get("rtsp_port", 554)),
            rtsp_path=data.get("rtsp_path", "/live/ch0"),
            username=data.get("username", ""),
            password=data.get("password", ""),
            onvif_port=int(data.get("onvif_port", 80)),
            enabled=data.get("enabled", True),
            vendor_model=data.get("vendor_model"),
            last_seen=data.get("last_seen"),
            camera_type=data.get("camera_type", "generic"),
            xm_port=int(data.get("xm_port", 34567)),
        )
