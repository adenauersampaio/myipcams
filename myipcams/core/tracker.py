import threading
import time
from typing import Callable, List, Optional
from .camera import Camera
from ..network.arp import ARPTable, normalize_mac
from ..network.discovery import NetworkDiscovery


class IPTracker:
    """
    Rastreador em segundo plano responsável por monitorar as câmeras e
    detectar alterações dinâmicas de endereço IP via ARP e WS-Discovery ONVIF.
    """

    def __init__(
        self,
        get_cameras_fn: Callable[[], List[Camera]],
        on_ip_changed: Optional[Callable[[Camera, str, str], None]] = None,
        check_interval: float = 30.0,
    ):
        self.get_cameras_fn = get_cameras_fn
        self.on_ip_changed = on_ip_changed
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="IPTrackerThread")
        self._thread.start()
        print("[IPTracker] Monitor de IP iniciado.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print("[IPTracker] Monitor de IP finalizado.")

    def _run_loop(self):
        while self._running:
            try:
                self.check_all_cameras()
            except Exception as e:
                print(f"[IPTracker] Erro no ciclo de verificação: {e}")

            # Dorme em pequenos passos para responder rápido ao stop()
            elapsed = 0.0
            while self._running and elapsed < self.check_interval:
                time.sleep(0.5)
                elapsed += 0.5

    def check_all_cameras(self):
        """Verifica todas as câmeras cadastradas contra as tabelas de rede."""
        cameras = self.get_cameras_fn()
        if not cameras:
            return

        # 1. Obter tabela ARP local (baixo custo de CPU e rede)
        arp_map = ARPTable.get_mac_to_ip_map()

        needs_discovery = False

        for cam in cameras:
            if not cam.enabled:
                continue

            # Se a câmera ainda não tem serial salvo, tenta obter via ONVIF
            if not cam.serial_number:
                try:
                    serial, model, _ = NetworkDiscovery.fetch_device_info(cam.current_ip, timeout=0.6)
                    if serial:
                        cam.serial_number = serial
                        print(f"[IPTracker] Serial Number auto-detectado para '{cam.name}': {serial}")
                    if model and not cam.vendor_model:
                        cam.vendor_model = model
                except Exception:
                    pass

            # Se temos o MAC cadastrado, verifica se o IP mudou na tabela ARP
            if cam.mac_address:
                norm_mac = normalize_mac(cam.mac_address)
                current_arp_ip = arp_map.get(norm_mac)
                if current_arp_ip:
                    if current_arp_ip != cam.current_ip:
                        old_ip = cam.current_ip
                        cam.update_ip(current_arp_ip)
                        print(f"[IPTracker] IP da câmera '{cam.name}' mudou: {old_ip} -> {current_arp_ip} (via ARP)")
                        if self.on_ip_changed:
                            self.on_ip_changed(cam, old_ip, current_arp_ip)
                else:
                    # MAC não consta na tabela ARP, pode ter expirado ou mudado (ex: câmeras que variam de MAC)
                    needs_discovery = True
            else:
                # Câmera sem MAC cadastrado ainda: tenta preencher
                mac = ARPTable.find_mac_by_ip(cam.current_ip)
                if mac:
                    cam.mac_address = mac
                    print(f"[IPTracker] MAC descoberto para câmera '{cam.name}': {mac}")
                else:
                    needs_discovery = True

        # 2. Se alguma câmera não foi resolvida via ARP ou precisa atualizar, dispara WS-Discovery
        if needs_discovery:
            self._discover_and_update(cameras)

    def locate_camera_now(self, camera: Camera) -> Optional[str]:
        """Tenta encontrar o novo IP de uma câmera imediatamente (ex: ao detectar stream offline)."""
        # Passo 1: Busca prioritária por Número de Série (imune a alternância de MAC)
        if camera.serial_number:
            discovered = NetworkDiscovery.discover_onvif(timeout=1.5)
            for disc in discovered:
                if disc.serial_number and disc.serial_number.lower() == camera.serial_number.lower():
                    if disc.mac and disc.mac != camera.mac_address:
                        camera.mac_address = disc.mac
                    if disc.uuid and not camera.onvif_uuid:
                        camera.onvif_uuid = disc.uuid
                    if disc.hardware and not camera.vendor_model:
                        camera.vendor_model = disc.hardware
                    if disc.ip != camera.current_ip:
                        old_ip = camera.current_ip
                        camera.update_ip(disc.ip)
                        print(f"[IPTracker] IP da câmera '{camera.name}' mudou: {old_ip} -> {disc.ip} (via Serial)")
                        if self.on_ip_changed:
                            self.on_ip_changed(camera, old_ip, disc.ip)
                        return disc.ip
                    return camera.current_ip

        # Passo 2: ARP direto
        if camera.mac_address:
            ip = ARPTable.find_ip_by_mac(camera.mac_address)
            if ip and ip != camera.current_ip:
                old_ip = camera.current_ip
                camera.update_ip(ip)
                if self.on_ip_changed:
                    self.on_ip_changed(camera, old_ip, ip)
                return ip

        # Passo 3: WS-Discovery (MAC e UUID)
        discovered = NetworkDiscovery.discover_onvif(timeout=1.5)
        for disc in discovered:
            matched = False
            if camera.serial_number and disc.serial_number and camera.serial_number.lower() == disc.serial_number.lower():
                matched = True
            elif camera.mac_address and disc.mac and normalize_mac(camera.mac_address) == normalize_mac(disc.mac):
                matched = True
            elif camera.onvif_uuid and disc.uuid and camera.onvif_uuid == disc.uuid:
                matched = True

            if matched:
                if disc.serial_number and not camera.serial_number:
                    camera.serial_number = disc.serial_number
                if disc.mac and not camera.mac_address:
                    camera.mac_address = disc.mac
                if disc.uuid and not camera.onvif_uuid:
                    camera.onvif_uuid = disc.uuid

                if disc.ip != camera.current_ip:
                    old_ip = camera.current_ip
                    camera.update_ip(disc.ip)
                    if self.on_ip_changed:
                        self.on_ip_changed(camera, old_ip, disc.ip)
                    return disc.ip
                return camera.current_ip

        return None

    def _discover_and_update(self, cameras: List[Camera]):
        discovered = NetworkDiscovery.discover_onvif(timeout=2.0)
        for disc in discovered:
            for cam in cameras:
                matched = False
                # 1. Prioridade máxima: Número de Série (imutável mesmo se o MAC variar)
                if cam.serial_number and disc.serial_number and cam.serial_number.lower() == disc.serial_number.lower():
                    matched = True
                elif cam.mac_address and disc.mac and normalize_mac(cam.mac_address) == normalize_mac(disc.mac):
                    matched = True
                elif cam.onvif_uuid and disc.uuid and cam.onvif_uuid == disc.uuid:
                    matched = True
                elif cam.current_ip == disc.ip:
                    # Mesmo IP: atualiza os metadados faltantes (Serial / MAC / UUID)
                    if disc.serial_number and not cam.serial_number:
                        cam.serial_number = disc.serial_number
                        print(f"[IPTracker] Serial Number vinculado para '{cam.name}': {disc.serial_number}")
                    if disc.mac and not cam.mac_address:
                        cam.mac_address = disc.mac
                    if disc.uuid and not cam.onvif_uuid:
                        cam.onvif_uuid = disc.uuid
                    if disc.hardware and not cam.vendor_model:
                        cam.vendor_model = disc.hardware

                if matched:
                    if disc.serial_number and not cam.serial_number:
                        cam.serial_number = disc.serial_number
                        print(f"[IPTracker] Serial Number vinculado para '{cam.name}': {disc.serial_number}")
                    if disc.mac and cam.mac_address != disc.mac:
                        # O MAC da câmera mudou (ex: Wi-Fi vs Ethernet ou alternância)! Atualiza para o novo MAC
                        cam.mac_address = disc.mac
                    if disc.uuid and not cam.onvif_uuid:
                        cam.onvif_uuid = disc.uuid
                    if disc.hardware and not cam.vendor_model:
                        cam.vendor_model = disc.hardware

                    if disc.ip != cam.current_ip:
                        old_ip = cam.current_ip
                        cam.update_ip(disc.ip)
                        print(f"[IPTracker] IP da câmera '{cam.name}' mudou: {old_ip} -> {disc.ip} (via Descoberta)")
                        if self.on_ip_changed:
                            self.on_ip_changed(cam, old_ip, disc.ip)
