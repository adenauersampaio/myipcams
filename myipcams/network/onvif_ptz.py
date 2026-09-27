import base64
from datetime import datetime, timezone
import hashlib
import logging
import os
import urllib.parse
from typing import Optional, Tuple
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)


def generate_wsse_header(username: str, password: str) -> str:
    """Gera o cabeçalho SOAP WS-Security com UsernameToken e digest de senha."""
    if not username:
        return ""
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    nonce_raw = os.urandom(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode("ascii")

    # Password_Digest = Base64(SHA-1(nonce + created + password))
    sha1 = hashlib.sha1()
    sha1.update(nonce_raw + created.encode("utf-8") + password.encode("utf-8"))
    digest_b64 = base64.b64encode(sha1.digest()).decode("ascii")

    return f"""
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
        <wsse:UsernameToken>
            <wsse:Username>{username}</wsse:Username>
            <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest_b64}</wsse:Password>
            <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</wsse:Nonce>
            <wsu:Created>{created}</wsu:Created>
        </wsse:UsernameToken>
    </wsse:Security>
    """


class ONVIFPTZClient:
    """Cliente leve para controle PTZ via padrão ONVIF SOAP (portas 80, 8080, 8899, etc.)."""

    def __init__(self, ip: str, port: int = 80, username: str = "", password: str = "", timeout: float = 2.5):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ptz_service_url: Optional[str] = None
        self.profile_token: Optional[str] = None
        self._initialized = False

    def _get_service_endpoints(self):
        """Descobre os endpoints dos serviços ONVIF (Device e PTZ) e os ProfileTokens."""
        wsse = generate_wsse_header(self.username, self.password)

        # 1. Tenta obter profiles a partir de /onvif/media_service ou /onvif/device_service
        media_url = f"http://{self.ip}:{self.port}/onvif/media_service"
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <soap:Header>{wsse}</soap:Header>
  <soap:Body>
    <trt:GetProfiles/>
  </soap:Body>
</soap:Envelope>"""
        try:
            resp = requests.post(
                media_url,
                data=body.encode("utf-8"),
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for elem in root.iter():
                    if elem.tag.endswith("Profiles"):
                        token = elem.attrib.get("token")
                        if token:
                            self.profile_token = token
                            break
        except Exception as e:
            logger.debug(f"Falha ao obter profiles ONVIF em {self.ip}:{self.port}: {e}")

        # Se não obteve perfil, usa token padrão comumente aceito
        if not self.profile_token:
            self.profile_token = "Profile000"

        self.ptz_service_url = f"http://{self.ip}:{self.port}/onvif/ptz_service"
        self._initialized = True

    def move(self, direction: str, speed: int = 4) -> bool:
        """Envia comando ContinuousMove ONVIF."""
        if not self._initialized:
            self._get_service_endpoints()

        # Mapeia velocidade de 1..8 para 0.1..1.0
        normalized_speed = max(0.1, min(1.0, speed / 8.0))
        x, y = 0.0, 0.0

        d = direction.lower()
        if "up" in d:
            y = normalized_speed
        elif "down" in d:
            y = -normalized_speed

        if "left" in d:
            x = -normalized_speed
        elif "right" in d:
            x = normalized_speed

        wsse = generate_wsse_header(self.username, self.password)
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ptz="http://www.onvif.org/ver20/ptz/wsdl" xmlns:tt="http://www.onvif.org/ver10/schema">
  <soap:Header>{wsse}</soap:Header>
  <soap:Body>
    <ptz:ContinuousMove>
      <ptz:ProfileToken>{self.profile_token or 'Profile000'}</ptz:ProfileToken>
      <ptz:Velocity>
        <tt:PanTilt x="{x:.2f}" y="{y:.2f}"/>
      </ptz:Velocity>
    </ptz:ContinuousMove>
  </soap:Body>
</soap:Envelope>"""

        # Tenta endpoints comuns de PTZ
        urls = [
            self.ptz_service_url,
            f"http://{self.ip}:{self.port}/onvif/ptz_service",
            f"http://{self.ip}:{self.port}/onvif/PTZ",
            f"http://{self.ip}:{self.port}/onvif/ptz",
        ]
        for url in dict.fromkeys(urls):
            try:
                resp = requests.post(
                    url,
                    data=body.encode("utf-8"),
                    headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    self.ptz_service_url = url
                    return True
            except Exception:
                continue
        return False

    def stop(self) -> bool:
        """Envia comando Stop ONVIF."""
        if not self._initialized:
            self._get_service_endpoints()

        wsse = generate_wsse_header(self.username, self.password)
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ptz="http://www.onvif.org/ver20/ptz/wsdl">
  <soap:Header>{wsse}</soap:Header>
  <soap:Body>
    <ptz:Stop>
      <ptz:ProfileToken>{self.profile_token or 'Profile000'}</ptz:ProfileToken>
      <ptz:PanTilt>true</ptz:PanTilt>
      <ptz:Zoom>true</ptz:Zoom>
    </ptz:Stop>
  </soap:Body>
</soap:Envelope>"""

        urls = [
            self.ptz_service_url,
            f"http://{self.ip}:{self.port}/onvif/ptz_service",
            f"http://{self.ip}:{self.port}/onvif/PTZ",
            f"http://{self.ip}:{self.port}/onvif/ptz",
        ]
        for url in dict.fromkeys(urls):
            try:
                resp = requests.post(
                    url,
                    data=body.encode("utf-8"),
                    headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    def reboot(self) -> bool:
        """Envia comando SystemReboot via ONVIF Device Management."""
        wsse = generate_wsse_header(self.username, self.password)
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <soap:Header>{wsse}</soap:Header>
  <soap:Body>
    <tds:SystemReboot/>
  </soap:Body>
</soap:Envelope>"""

        device_urls = [
            f"http://{self.ip}:{self.port}/onvif/device_service",
            f"http://{self.ip}:{self.port}/onvif/Device",
            f"http://{self.ip}:{self.port}/device_service",
            f"http://{self.ip}:{self.port}/onvif/devices",
        ]

        # Tenta primeiro SOAP 1.2 e fallback para SOAP 1.1 se necessário
        header_variants = [
            {"Content-Type": "application/soap+xml; charset=utf-8; action=\"http://www.onvif.org/ver10/device/wsdl/SystemReboot\""},
            {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "\"http://www.onvif.org/ver10/device/wsdl/SystemReboot\""},
        ]

        for url in device_urls:
            for headers in header_variants:
                try:
                    resp = requests.post(
                        url,
                        data=body.encode("utf-8"),
                        headers=headers,
                        timeout=self.timeout,
                    )
                    if resp.status_code == 200 or "SystemRebootResponse" in resp.text:
                        logger.info(f"Comando de reboot ONVIF aceito com sucesso por {url}")
                        return True
                except Exception as e:
                    logger.debug(f"Falha de reboot ONVIF em {url} ({e})")
                    continue
        return False

    def check_audio_support(self) -> Tuple[bool, bool]:
        """Verifica se o perfil ONVIF possui entrada de áudio (microfone) e/ou saída (alto-falante).
        
        Retorna: (has_mic, has_speaker)
        """
        wsse = generate_wsse_header(self.username, self.password)
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <soap:Header>{wsse}</soap:Header>
  <soap:Body>
    <trt:GetProfiles/>
  </soap:Body>
</soap:Envelope>"""

        media_urls = [
            f"http://{self.ip}:{self.port}/onvif/media_service",
            f"http://{self.ip}:{self.port}/onvif/Media",
            f"http://{self.ip}:{self.port}/media_service",
        ]
        for url in media_urls:
            try:
                resp = requests.post(
                    url,
                    data=body.encode("utf-8"),
                    headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    text = resp.text.lower()
                    has_mic = "audioencoderconfiguration" in text or "audiosource" in text
                    has_speaker = "audiooutput" in text or "backchannel" in text
                    return (has_mic, has_speaker)
            except Exception:
                continue

        return (False, False)
