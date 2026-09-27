import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    """Normaliza um endereço MAC para o formato minúsculo 'aa:bb:cc:dd:ee:ff'."""
    if not mac:
        return None
    mac = mac.strip().lower()
    # Se contém separadores (: ou -), formata cada octeto com 2 dígitos hexadecimais
    if ":" in mac or "-" in mac:
        sep = ":" if ":" in mac else "-"
        parts = mac.split(sep)
        if len(parts) == 6:
            try:
                return ":".join(f"{int(p, 16):02x}" for p in parts)
            except ValueError:
                return None
    # Sem separadores: remove caracteres não hexadecimais
    clean = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
    if len(clean) != 12:
        return None
    return ":".join(clean[i:i+2] for i in range(0, 12, 2))


def parse_arp_output(output: str) -> Dict[str, str]:
    """
    Interpreta saídas de comandos ARP (arp -a, arp -an) comuns em Windows, macOS e Unix.
    Retorna dicionário mapeando MAC normalizado para IP.
    """
    mapping: Dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # Formato macOS / BSD: "? (192.168.1.1) at 0:14:22:1:23:45 on en0 ifscope [ethernet]"
        m_bsd = re.search(r"\(([0-9]{1,3}(?:\.[0-9]{1,3}){3})\)\s+at\s+([0-9a-fA-F:]{1,17})", line)
        if m_bsd:
            ip, raw_mac = m_bsd.group(1), m_bsd.group(2)
            if raw_mac != "(incomplete)":
                norm = normalize_mac(raw_mac)
                if norm and norm != "ff:ff:ff:ff:ff:ff":
                    mapping[norm] = ip
            continue

        # Formato Windows / Unix padrão: "192.168.1.1   00-14-22-01-23-45   dynamic"
        m_std = re.search(r"([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F[:-]{11,17})", line)
        if m_std:
            ip, raw_mac = m_std.group(1), m_std.group(2)
            norm = normalize_mac(raw_mac)
            if norm and norm != "ff:ff:ff:ff:ff:ff":
                mapping[norm] = ip

    return mapping


class ARPTable:
    """Inspeção e resolução de IPs e endereços MAC na tabela ARP de forma multiplataforma (Linux, Windows, macOS)."""

    @staticmethod
    def get_mac_to_ip_map() -> Dict[str, str]:
        """
        Retorna um dicionário mapeando endereço MAC normalizado para IP atual.
        Ex: {"a4:12:42:3b:01:2c": "192.168.1.120"}
        """
        mac_to_ip: Dict[str, str] = {}

        # 1. No Linux: Leitura ultrarrápida direta de /proc/net/arp
        proc_arp = Path("/proc/net/arp")
        if proc_arp.exists():
            try:
                with open(proc_arp, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00":
                            norm_mac = normalize_mac(mac)
                            if norm_mac:
                                mac_to_ip[norm_mac] = ip
            except Exception as e:
                print(f"[ARP] Erro ao ler /proc/net/arp: {e}")

        # 2. No Linux: Fallback / complemento com 'ip neigh'
        if sys.platform.startswith("linux"):
            try:
                res = subprocess.run(
                    ["ip", "-4", "neigh"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        parts = line.strip().split()
                        if "lladdr" in parts:
                            idx = parts.index("lladdr")
                            if idx + 1 < len(parts):
                                ip = parts[0]
                                mac = parts[idx + 1]
                                norm_mac = normalize_mac(mac)
                                if norm_mac and norm_mac not in mac_to_ip:
                                    mac_to_ip[norm_mac] = ip
            except Exception:
                pass

        # 3. No Windows, macOS ou quando os métodos do Linux não retornaram entradas
        if not mac_to_ip or sys.platform.startswith("win") or sys.platform == "darwin":
            try:
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
                cmd = ["arp", "-a"] if not sys.platform == "darwin" else ["arp", "-an"]
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                    creationflags=creation_flags
                )
                if res.returncode == 0 and res.stdout:
                    parsed = parse_arp_output(res.stdout)
                    for k, v in parsed.items():
                        if k not in mac_to_ip:
                            mac_to_ip[k] = v
            except Exception:
                pass

        return mac_to_ip

    @classmethod
    def find_ip_by_mac(cls, target_mac: str) -> Optional[str]:
        norm = normalize_mac(target_mac)
        if not norm:
            return None
        table = cls.get_mac_to_ip_map()
        return table.get(norm)

    @classmethod
    def find_mac_by_ip(cls, target_ip: str) -> Optional[str]:
        target_ip = target_ip.strip()
        table = cls.get_mac_to_ip_map()
        for mac, ip in table.items():
            if ip == target_ip:
                return mac
        return None

    @staticmethod
    def trigger_arp_refresh(ip: str):
        """Envia um ping rápido de 1 pacote para forçar a pilha de rede a atualizar a entrada ARP."""
        try:
            if sys.platform.startswith("win"):
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            elif sys.platform == "darwin":
                cmd = ["ping", "-c", "1", "-W", "1000", ip]
                creation_flags = 0
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip]
                creation_flags = 0

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
        except Exception:
            pass

