import os
import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap


def get_project_root() -> Path:
    """Retorna o diretório raiz do projeto myipcams."""
    return Path(__file__).resolve().parent.parent.parent


def get_asset_path(filename: str) -> Optional[Path]:
    """
    Busca o caminho absoluto de um arquivo de asset procurando em múltiplos locais comuns:
    1. Raiz do projeto / assets
    2. Pacote myipcams / assets (caso empacotado)
    3. Diretório padrão XDG do usuário (~/.local/share/myipcams/assets)
    4. Diretório compartilhado do sistema (/usr/share/myipcams/assets)
    5. Diretório de dados no Windows (%LOCALAPPDATA%/myipcams/assets)
    6. Diretório de dados no macOS (~/Library/Application Support/myipcams/assets)
    """
    candidates = [
        get_project_root() / "assets" / filename,
        Path(__file__).resolve().parent.parent / "assets" / filename,
        Path.home() / ".local" / "share" / "myipcams" / "assets" / filename,
        Path("/usr/share/myipcams/assets") / filename,
    ]

    # Windows AppData
    if sys.platform.startswith("win"):
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(Path(local_appdata) / "myipcams" / "assets" / filename)

    # macOS Application Support
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "myipcams" / "assets" / filename)

    candidates.append(Path("assets") / filename)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None



def get_app_icon() -> QIcon:
    """
    Retorna o QIcon do aplicativo MyIPCams com múltiplas resoluções
    para renderização nítida em qualquer DPI/resolução de tela.
    """
    icon = QIcon()

    # Tenta carregar ícones PNG gerados em várias resoluções
    sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    loaded_any = False
    for sz in sizes:
        p = get_asset_path(f"icon_{sz}.png")
        if p and p.is_file():
            icon.addFile(str(p))
            loaded_any = True

    # Imagem principal PNG ou JPG
    for main_name in ["myipcams.png", "App_icon_for_MyIPCams_2K_20260927120318.jpg"]:
        p = get_asset_path(main_name)
        if p and p.is_file():
            icon.addFile(str(p))
            loaded_any = True

    return icon


def get_camera_animation_path() -> Optional[str]:
    """Retorna o caminho do GIF animado da câmera de segurança."""
    p = get_asset_path("Security_camera_pans_left_right_20260927120805.gif")
    return str(p) if p else None


def get_camera_video_path() -> Optional[str]:
    """Retorna o caminho do vídeo MP4 da câmera de segurança."""
    p = get_asset_path("Security_camera_pans_left_right_20260927120723.mp4")
    return str(p) if p else None
