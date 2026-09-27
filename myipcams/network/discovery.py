import concurrent.futures
from dataclasses import dataclass, field
import ipaddress
import re
import socket
import struct
import subprocess
import sys
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional, Set
from .arp import ARPTable, normalize_mac



WS_DISCOVERY_TEMPLATES = [
    # Probe 1: Padrão tds:Device
    """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
          xmlns="http://www.w3.org/2003/05/soap-envelope">
    <Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
        <wsa:MessageID>urn:uuid:{msg_id}</wsa:MessageID>
        <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
        <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    </Header>
    <Body>
        <Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
            <Types>tds:Device</Types>
        </Probe>
    </Body>
</Envelope>""",
    # Probe 2: dn:NetworkVideoTransmitter (comum em Hikvision / Dahua / Vivotek)
    """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl"
          xmlns="http://www.w3.org/2003/05/soap-envelope">
    <Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
        <wsa:MessageID>urn:uuid:{msg_id}</wsa:MessageID>
        <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
        <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    </Header>
    <Body>
        <Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
            <Types>dn:NetworkVideoTransmitter</Types>
        </Probe>
    </Body>
</Envelope>""",
    # Probe 3: Wildcard (sem filtro de tipos)
    """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
    <Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
        <wsa:MessageID>urn:uuid:{msg_id}</wsa:MessageID>
        <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
        <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    </Header>
    <Body>
        <Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery" />
    </Body>
</Envelope>""",
]

# Portas padrão tipicamente abertas em câmeras IP e servidores de streaming
CAMERA_PORTS = [
    554,    # RTSP (Porta padrão de vídeo)
    80,     # HTTP (Web / ONVIF)
    8080,   # HTTP alternativo / ONVIF
    8000,   # Hikvision SDK / ONVIF
    8899,   # Xiongmai / Sofia ONVIF
    37777,  # Dahua / Intelbras DVR/IPC
    34567,  # Xiongmai / ICSee DVR/IPC
]


@dataclass
class DiscoveredCamera:
    ip: str
    port: int = 80
    rtsp_port: int = 554
    mac: Optional[str] = None
    uuid: Optional[str] = None
    name: Optional[str] = None
    hardware: Optional[str] = None
    xaddrs: Optional[str] = None
    protocol: str = "ONVIF"
    open_ports: List[int] = field(default_factory=list)
    server_banner: Optional[str] = None

    def to_display_string(self) -> str:
        parts = [f"IP: {self.ip}"]
        if self.name:
            parts.append(f"Nome: {self.name}")
        if self.hardware:
            parts.append(f"Modelo: {self.hardware}")
        if self.open_ports:
            parts.append(f"Portas: {','.join(map(str, self.open_ports))}")
        if self.mac:
            parts.append(f"MAC: {self.mac}")
        return " | ".join(parts)


class NetworkDiscovery:
    """
    Mecanismo híbrido de descoberta de câmeras na rede local:
    1. WS-Discovery (ONVIF) com múltiplos probes e suporte a broadcast/multicast.
    2. Varredura completa da sub-rede por portas (RTSP 554, HTTP 80/8080, portas de fabricantes).
    3. Resolução automática de MAC via tabela ARP do kernel.
    """

    MULTICAST_GROUP = "239.255.255.250"
    WS_PORT = 3702

    @staticmethod
    def get_local_subnets() -> List[str]:
        """Detecta as sub-redes IPv4 locais disponíveis de forma multiplataforma (Linux, Windows, macOS)."""
        subnets = []

        # 1. No Linux: comando 'ip'
        if sys.platform.startswith("linux"):
            try:
                res = subprocess.run(["ip", "-o", "-4", "addr", "show"], capture_output=True, text=True, timeout=1.5)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        parts = line.strip().split()
                        if "inet" in parts:
                            idx = parts.index("inet")
                            if idx + 1 < len(parts):
                                cidr = parts[idx + 1]
                                ip = cidr.split("/")[0]
                                if not ip.startswith("127.") and not ip.startswith("169.254."):
                                    net = ipaddress.ip_network(cidr, strict=False)
                                    subnets.append(str(net))
            except Exception:
                pass

        # 2. No Windows: comando 'ipconfig'
        elif sys.platform.startswith("win"):
            try:
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                res = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=1.5, creationflags=creation_flags)
                if res.returncode == 0:
                    ips = re.findall(r"IPv4[^:]*:\s*([0-9.]+)", res.stdout)
                    masks = re.findall(r"Subnet Mask[^:]*:\s*([0-9.]+)", res.stdout)
                    for ip, mask in zip(ips, masks):
                        if not ip.startswith("127.") and not ip.startswith("169.254."):
                            try:
                                net = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
                                subnets.append(str(net))
                            except Exception:
                                pass
            except Exception:
                pass

        # 3. No macOS: comando 'ifconfig'
        elif sys.platform == "darwin":
            try:
                res = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=1.5)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        m = re.search(r"inet\s+([0-9.]+)\s+netmask\s+(0x[0-9a-fA-F]+|[0-9.]+)", line)
                        if m:
                            ip, raw_mask = m.group(1), m.group(2)
                            if not ip.startswith("127.") and not ip.startswith("169.254."):
                                try:
                                    if raw_mask.startswith("0x"):
                                        mask_int = int(raw_mask, 16)
                                        mask_str = socket.inet_ntoa(struct.pack("!I", mask_int))
                                    else:
                                        mask_str = raw_mask
                                    net = ipaddress.ip_network(f"{ip}/{mask_str}", strict=False)
                                    subnets.append(str(net))
                                except Exception:
                                    pass
            except Exception:
                pass

        # 4. Fallback universal via socket UDP (funciona em qualquer SO conectado a rede/internet)
        if not subnets:
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip and not local_ip.startswith("127.") and not local_ip.startswith("169.254."):
                    net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
                    subnets.append(str(net))
            except Exception:
                subnets.append("192.168.1.0/24")
            finally:
                if s:
                    s.close()

        return list(dict.fromkeys(subnets))


    @classmethod
    def get_primary_subnet(cls) -> str:
        """Retorna a sub-rede mais provável da rede local física."""
        subnets = cls.get_local_subnets()
        for sub in subnets:
            if sub.startswith("192.168.") or sub.startswith("10."):
                return sub
        return subnets[0] if subnets else "192.168.1.0/24"

    @classmethod
    def discover_onvif(cls, timeout: float = 2.5) -> List[DiscoveredCamera]:
        """
        Dispara múltiplos probes WS-Discovery via multicast e broadcast UDP.
        Retorna lista de câmeras que responderam com metadados ONVIF.
        """
        cameras: List[DiscoveredCamera] = []
        seen_keys: Set[str] = set()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)

            # Envia probes para multicast e broadcast
            targets = [
                (cls.MULTICAST_GROUP, cls.WS_PORT),
                ("255.255.255.255", cls.WS_PORT),
            ]

            for tmpl in WS_DISCOVERY_TEMPLATES:
                msg = tmpl.format(msg_id=str(uuid.uuid4())).encode("utf-8")
                for target in targets:
                    try:
                        sock.sendto(msg, target)
                    except Exception:
                        pass

            # Coleta respostas até o timeout
            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                    reply_ip = addr[0]
                    cam = cls._parse_ws_probe_match(data.decode("utf-8", errors="ignore"), reply_ip)
                    if cam:
                        key = cam.mac or cam.uuid or cam.ip
                        if key not in seen_keys:
                            seen_keys.add(key)
                            cameras.append(cam)
                except socket.timeout:
                    break
                except Exception as e:
                    print(f"[Discovery] Erro ao receber resposta ONVIF: {e}")
                    break
        finally:
            sock.close()

        # Resolve MAC via ARP para câmeras que não reportaram MAC no XML
        for cam in cameras:
            if not cam.mac:
                cam.mac = ARPTable.find_mac_by_ip(cam.ip)

        return cameras

    @classmethod
    def _parse_ws_probe_match(cls, xml_text: str, fallback_ip: str) -> Optional[DiscoveredCamera]:
        """Extrai IP, XAddrs, UUID, Scopes e modelo a partir da resposta XML."""
        try:
            xaddrs_match = re.search(r"<[^>]*XAddrs[^>]*>(.*?)</[^>]*XAddrs[^>]*>", xml_text, re.DOTALL)
            xaddrs = xaddrs_match.group(1).strip() if xaddrs_match else ""

            uuid_match = re.search(r"<[^>]*Address[^>]*>(.*?)</[^>]*Address[^>]*>", xml_text, re.DOTALL)
            cam_uuid = uuid_match.group(1).strip() if uuid_match else None

            scopes_match = re.search(r"<[^>]*Scopes[^>]*>(.*?)</[^>]*Scopes[^>]*>", xml_text, re.DOTALL)
            scopes_text = scopes_match.group(1) if scopes_match else ""

            cam_name = None
            hardware = None
            for item in scopes_text.split():
                if "onvif://www.onvif.org/name/" in item:
                    cam_name = urllib.parse.unquote(item.replace("onvif://www.onvif.org/name/", ""))
                elif "onvif://www.onvif.org/hardware/" in item:
                    hardware = urllib.parse.unquote(item.replace("onvif://www.onvif.org/hardware/", ""))

            ip = fallback_ip
            port = 80
            if xaddrs:
                first_url = xaddrs.split()[0]
                parsed = urllib.parse.urlparse(first_url)
                if parsed.hostname:
                    ip = parsed.hostname
                if parsed.port:
                    port = parsed.port

            mac = ARPTable.find_mac_by_ip(ip)

            return DiscoveredCamera(
                ip=ip,
                port=port,
                rtsp_port=554,
                mac=mac,
                uuid=cam_uuid,
                name=cam_name or f"ONVIF ({ip})",
                hardware=hardware,
                xaddrs=xaddrs,
                protocol="ONVIF",
                open_ports=[port] if port != 80 else [80],
            )
        except Exception as e:
            print(f"[Discovery] Falha no parse do probe match: {e}")
            return None

    @staticmethod
    def probe_rtsp(ip: str, port: int = 554, timeout: float = 0.6) -> Optional[str]:
        """
        Envia uma requisição OPTIONS RTSP para validar se o serviço de vídeo está ativo
        e capturar o banner do servidor (ex: Hikvision, Dahua, Boa, etc.).
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            req = f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: MyIPCams\r\n\r\n"
            s.sendall(req.encode("ascii"))
            resp = s.recv(1024).decode("utf-8", errors="ignore")
            s.close()

            for line in resp.splitlines():
                if line.lower().startswith("server:"):
                    return line.split(":", 1)[1].strip()
            return "RTSP Server"
        except Exception:
            return None

    @staticmethod
    def check_port(ip: str, port: int, timeout: float = 0.4) -> bool:
        """Testa se uma porta TCP específica está aberta."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            return result == 0
        except Exception:
            return False

    @classmethod
    def scan_host(cls, ip: str) -> Optional[DiscoveredCamera]:
        """
        Testa um endereço IP para portas típicas de câmeras de vídeo e CFTV.
        Retorna DiscoveredCamera se pelo menos uma porta relevante estiver aberta.
        """
        open_ports = []
        is_rtsp = False
        rtsp_banner = None

        # 1. Testa a porta 554 (RTSP) primeiro
        if cls.check_port(ip, 554, timeout=0.35):
            open_ports.append(554)
            is_rtsp = True
            rtsp_banner = cls.probe_rtsp(ip, 554, timeout=0.5)

        # 2. Testa demais portas de câmeras
        for p in CAMERA_PORTS:
            if p == 554:
                continue
            if cls.check_port(ip, p, timeout=0.35):
                open_ports.append(p)

        if not open_ports:
            return None

        # Tenta capturar o MAC via ARP (o handshake TCP garante atualização da tabela ARP pelo kernel)
        mac = ARPTable.find_mac_by_ip(ip)

        # Determina nome e modelo aproximados
        name_parts = []
        hardware = None
        if rtsp_banner and rtsp_banner != "RTSP Server":
            hardware = rtsp_banner
            name_parts.append(rtsp_banner)
        elif 554 in open_ports:
            name_parts.append(f"Câmera RTSP ({ip})")
        elif 37777 in open_ports:
            name_parts.append(f"Dahua/Intelbras ({ip})")
            hardware = "Dahua/Intelbras"
        elif 34567 in open_ports:
            name_parts.append(f"XM/ICSee ({ip})")
            hardware = "Xiongmai/ICSee"
        elif 8899 in open_ports:
            name_parts.append(f"ONVIF-Cam ({ip})")
        else:
            name_parts.append(f"Dispositivo ({ip})")

        cam_name = name_parts[0]
        protocol = "RTSP" if is_rtsp else "PortScan"
        web_port = 80
        for cand in [80, 8080, 8899, 8000]:
            if cand in open_ports:
                web_port = cand
                break

        return DiscoveredCamera(
            ip=ip,
            port=web_port,
            rtsp_port=554 if 554 in open_ports else 554,
            mac=mac,
            name=cam_name,
            hardware=hardware,
            protocol=protocol,
            open_ports=open_ports,
            server_banner=rtsp_banner,
        )

    @classmethod
    def scan_subnet(
        cls,
        subnet_str: str,
        max_workers: int = 50,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[DiscoveredCamera]:
        """
        Executa uma varredura completa da sub-rede especificada testando portas de câmeras em paralelo.
        """
        cameras: List[DiscoveredCamera] = []
        try:
            network = ipaddress.ip_network(subnet_str, strict=False)
            hosts = [str(h) for h in network.hosts()]
        except Exception as e:
            print(f"[Discovery] Formato de sub-rede inválido '{subnet_str}': {e}")
            return cameras

        total = len(hosts)
        completed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(cls.scan_host, ip): ip for ip in hosts}
            for future in concurrent.futures.as_completed(future_to_ip):
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                try:
                    result = future.result()
                    if result:
                        cameras.append(result)
                except Exception:
                    pass

        return cameras

    @classmethod
    def discover_all(
        cls,
        subnet_str: Optional[str] = None,
        run_subnet_scan: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[DiscoveredCamera]:
        """
        Executa a descoberta unificada (ONVIF + Varredura de Sub-rede),
        mesclando resultados para garantir que todas as câmeras sejam encontradas
        sem duplicação.
        """
        cameras_by_ip = {}

        # 1. Primeiro executa a busca ONVIF (rápida, multicast)
        onvif_cams = cls.discover_onvif(timeout=2.0)
        for cam in onvif_cams:
            cameras_by_ip[cam.ip] = cam

        # 2. Se habilitado, executa a varredura completa de sub-rede
        if run_subnet_scan:
            target_subnet = subnet_str or cls.get_primary_subnet()
            subnet_cams = cls.scan_subnet(target_subnet, progress_callback=progress_callback)

            for scam in subnet_cams:
                if scam.ip in cameras_by_ip:
                    existing = cameras_by_ip[scam.ip]
                    if not existing.mac and scam.mac:
                        existing.mac = scam.mac
                    if not existing.hardware and scam.hardware:
                        existing.hardware = scam.hardware
                    for p in scam.open_ports:
                        if p not in existing.open_ports:
                            existing.open_ports.append(p)
                    existing.protocol = "ONVIF + RTSP" if 554 in existing.open_ports else "ONVIF"
                else:
                    cameras_by_ip[scam.ip] = scam
        elif progress_callback:
            progress_callback(100, 100)

        return list(cameras_by_ip.values())
